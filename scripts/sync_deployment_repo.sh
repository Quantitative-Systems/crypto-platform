#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Crypto Engine — Safe Remote Git Repository Synchronizer & Initializer
# ==============================================================================
# Invariants:
# 1. Reuses existing directory safely; never deletes application directory
# 2. Handles confirmed empty bootstrap directories (deploy/, scripts/) safely
# 3. Fails closed and reports unexpected files without deleting or overwriting
# 4. Validates Git repository origin and rejects dirty tracked files
# 5. Synchronizes and verifies exact target commit SHA
# ==============================================================================

resolve_clone_url() {
    local repo="$1"
    if [[ "${repo}" == https://* ]] || [[ "${repo}" == git@* ]] || [[ "${repo}" == file://* ]] || [[ -d "${repo}" ]]; then
        echo "${repo}"
    else
        echo "https://github.com/${repo}.git"
    fi
}

validate_bootstrap_dir() {
    local dir="$1"
    local unexpected=()

    while IFS= read -r item; do
        [ -z "${item}" ] && continue
        if [ "${item}" = "deploy" ] || [ "${item}" = "scripts" ]; then
            if [ ! -d "${dir}/${item}" ]; then
                unexpected+=("${item} (not a directory)")
            else
                local files_inside
                files_inside=$(find "${dir}/${item}" -type f 2>/dev/null || true)
                if [ -n "${files_inside}" ]; then
                    unexpected+=("${item} (contains existing files)")
                fi
            fi
        else
            unexpected+=("${item}")
        fi
    done < <(find "${dir}" -mindepth 1 -maxdepth 1 -printf "%f\n" 2>/dev/null || (cd "${dir}" 2>/dev/null && ls -A1 2>/dev/null))

    if [ ${#unexpected[@]} -gt 0 ]; then
        echo "FATAL: Destination directory '${dir}' exists without Git metadata and contains unexpected files/directories:" >&2
        for u in "${unexpected[@]}"; do
            echo "  - ${u}" >&2
        done
        return 1
    fi
    return 0
}

sync_repo() {
    local target_dir="${1:-}"
    local expected_repo="${2:-}"
    local target_ref="${3:-}"
    local target_sha="${4:-}"

    if [ -z "${target_dir}" ] || [ -z "${expected_repo}" ] || [ -z "${target_ref}" ] || [ -z "${target_sha}" ]; then
        echo "Usage: sync_repo <target_dir> <expected_repo> <target_ref> <target_sha>" >&2
        return 1
    fi

    local clone_url
    clone_url=$(resolve_clone_url "${expected_repo}")

    # Case 1: Destination exists as a valid Git repository
    if [ -d "${target_dir}/.git" ] && git -C "${target_dir}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "Reusing existing Git repository at '${target_dir}'..."

        # Verify remote origin matches expected repository
        local remote_url
        remote_url=$(git -C "${target_dir}" config --get remote.origin.url || true)
        if [ -z "${remote_url}" ]; then
            echo "FATAL: Existing repository at '${target_dir}' has no remote.origin.url configured!" >&2
            return 1
        fi

        local lower_url lower_expected
        lower_url=$(echo "${remote_url}" | tr '[:upper:]' '[:lower:]' | sed -e 's/\.git$//')
        lower_expected=$(echo "${expected_repo}" | tr '[:upper:]' '[:lower:]' | sed -e 's/\.git$//')
        if [[ "${lower_url}" != *"${lower_expected}"* ]]; then
            echo "FATAL: Repository origin '${remote_url}' does not match expected repository '${expected_repo}'!" >&2
            return 1
        fi

        # Verify working tree has no unexpected local modifications to tracked files
        if [ -n "$(git -C "${target_dir}" status --porcelain -uno)" ]; then
            echo "FATAL: Repository at '${target_dir}' has unexpected local modifications in tracked files!" >&2
            git -C "${target_dir}" status --short -uno >&2
            return 1
        fi

        echo "Fetching revision '${target_ref}' from origin..."
        git -C "${target_dir}" fetch origin "${target_ref}"

        echo "Checking out target commit '${target_sha}'..."
        git -C "${target_dir}" checkout "${target_sha}"

    # Case 2: Destination does NOT exist OR is an empty bootstrap directory without Git metadata
    else
        local is_existing_bootstrap=false
        if [ -e "${target_dir}" ]; then
            if [ ! -d "${target_dir}" ]; then
                echo "FATAL: Destination '${target_dir}' exists but is not a directory!" >&2
                return 1
            fi

            # Validate that directory contains ONLY allowed empty bootstrap directories (deploy/, scripts/)
            if ! validate_bootstrap_dir "${target_dir}"; then
                echo "Aborting initialization to prevent data loss or overwriting unexpected content." >&2
                return 1
            fi
            is_existing_bootstrap=true
            echo "Confirmed empty deployment bootstrap directory at '${target_dir}'. Initializing safely..."
        else
            echo "Destination '${target_dir}' does not exist. Initializing new repository..."
        fi

        # Safe sibling temporary clone: failure during clone/checkout never damages target_dir
        local parent_dir
        parent_dir=$(dirname "${target_dir}")
        mkdir -p "${parent_dir}"
        local tmp_clone
        tmp_clone=$(mktemp -d "${parent_dir}/.crypto_platform_init_XXXXXX" 2>/dev/null || mktemp -d)

        echo "Cloning repository into temporary staging directory '${tmp_clone}'..."
        if ! git clone "${clone_url}" "${tmp_clone}"; then
            echo "FATAL: Failed to clone repository from '${clone_url}'!" >&2
            rm -rf "${tmp_clone}"
            return 1
        fi

        if ! git -C "${tmp_clone}" fetch origin "${target_ref}"; then
            echo "FATAL: Failed to fetch target ref '${target_ref}' from '${clone_url}'!" >&2
            rm -rf "${tmp_clone}"
            return 1
        fi

        if ! git -C "${tmp_clone}" checkout "${target_sha}"; then
            echo "FATAL: Failed to checkout target SHA '${target_sha}' in staging directory!" >&2
            rm -rf "${tmp_clone}"
            return 1
        fi

        local staged_sha
        staged_sha=$(git -C "${tmp_clone}" rev-parse HEAD)
        if [ "${staged_sha}" != "${target_sha}" ]; then
            echo "FATAL: Staging revision mismatch! Expected '${target_sha}' but checked out '${staged_sha}'." >&2
            rm -rf "${tmp_clone}"
            return 1
        fi

        # Move into place
        if [ "${is_existing_bootstrap}" = true ]; then
            echo "Moving Git metadata into '${target_dir}' and populating work tree..."
            mv "${tmp_clone}/.git" "${target_dir}/.git"
            git -C "${target_dir}" checkout -f "${target_sha}"
            rm -rf "${tmp_clone}"
        else
            echo "Moving staging directory to '${target_dir}'..."
            mv "${tmp_clone}" "${target_dir}"
        fi
    fi

    # Cryptographic confirmation of current HEAD matching target_sha
    local current_sha
    current_sha=$(git -C "${target_dir}" rev-parse HEAD)
    echo "Verified deployment revision: ${current_sha}"
    if [ "${current_sha}" != "${target_sha}" ]; then
        echo "FATAL: Deployment revision mismatch! Expected '${target_sha}' but checked out '${current_sha}'." >&2
        return 1
    fi

    return 0
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    sync_repo "$@"
fi
