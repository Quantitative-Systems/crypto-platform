#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Crypto Engine — Safe Remote Git Repository Synchronizer
# ==============================================================================
# Invariants:
# 1. Reuses existing directory safely; never deletes application directory
# 2. Verifies destination is a valid Git repo with expected origin
# 3. Fails safely on dirty tracked files
# 4. Synchronizes and verifies exact target commit SHA
# ==============================================================================

sync_repo() {
    local target_dir="${1:-}"
    local expected_repo="${2:-}"
    local target_ref="${3:-}"
    local target_sha="${4:-}"

    if [ -z "${target_dir}" ] || [ -z "${expected_repo}" ] || [ -z "${target_ref}" ] || [ -z "${target_sha}" ]; then
        echo "Usage: sync_repo <target_dir> <expected_repo> <target_ref> <target_sha>" >&2
        return 1
    fi

    # Case 1: Directory does not exist yet -> perform initial clone
    if [ ! -e "${target_dir}" ]; then
        echo "Destination '${target_dir}' does not exist. Performing initial clone..."
        if [[ "${expected_repo}" == https://* ]] || [[ "${expected_repo}" == git@* ]] || [[ "${expected_repo}" == file://* ]] || [[ -d "${expected_repo}" ]]; then
            git clone "${expected_repo}" "${target_dir}"
        else
            git clone "https://github.com/${expected_repo}.git" "${target_dir}"
        fi
    fi

    # Case 2: Destination exists but is not a directory
    if [ ! -d "${target_dir}" ]; then
        echo "FATAL: Destination '${target_dir}' exists but is not a directory!" >&2
        return 1
    fi

    # Case 3: Destination exists as a directory -> verify it is a valid Git repository
    if ! git -C "${target_dir}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "FATAL: Destination directory '${target_dir}' exists but is not a valid Git repository!" >&2
        return 1
    fi

    # Case 4: Verify remote origin matches expected repository
    local remote_url
    remote_url=$(git -C "${target_dir}" config --get remote.origin.url || true)
    if [ -z "${remote_url}" ]; then
        echo "FATAL: Existing repository at '${target_dir}' has no remote.origin.url configured!" >&2
        return 1
    fi

    # Normalize URLs to check repository slug (supports https:// or git@ or local path for tests)
    local lower_url lower_expected
    lower_url=$(echo "${remote_url}" | tr '[:upper:]' '[:lower:]' | sed -e 's/\.git$//')
    lower_expected=$(echo "${expected_repo}" | tr '[:upper:]' '[:lower:]' | sed -e 's/\.git$//')
    if [[ "${lower_url}" != *"${lower_expected}"* ]]; then
        echo "FATAL: Repository origin '${remote_url}' does not match expected repository '${expected_repo}'!" >&2
        return 1
    fi

    # Case 5: Verify working tree has no unexpected local modifications to tracked files
    # -uno ignores untracked data/runtime files (preserving persistent data without failing on untracked db/logs)
    if [ -n "$(git -C "${target_dir}" status --porcelain -uno)" ]; then
        echo "FATAL: Repository at '${target_dir}' has unexpected local modifications in tracked files!" >&2
        git -C "${target_dir}" status --short -uno >&2
        return 1
    fi

    # Case 6: Fetch intended ref and checkout exact target commit SHA
    echo "Fetching revision '${target_ref}' from origin..."
    git -C "${target_dir}" fetch origin "${target_ref}"

    echo "Checking out target commit '${target_sha}'..."
    git -C "${target_dir}" checkout "${target_sha}"

    # Case 7: Cryptographic confirmation of current HEAD matching target_sha
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
