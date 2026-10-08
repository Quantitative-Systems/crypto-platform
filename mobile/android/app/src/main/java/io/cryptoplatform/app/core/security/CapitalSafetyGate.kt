package io.cryptoplatform.app.core.security

/**
 * Immutable Client-Side Capital Safety Gate.
 * Enforces fail-closed safety constraints:
 * - Real Capital authorized is strictly $0.00
 * - Live Order routing is permanently disabled fail-closed
 * - Target Floor cannot be configured below 4.0R
 * - Risk per trade cannot exceed 1.0%
 * - Portfolio heat cannot exceed 3.0%
 */
object CapitalSafetyGate {

    const val REAL_CAPITAL_AUTHORIZED_USD: Double = 0.00
    const val IS_LIVE_TRADING_LOCKED: Boolean = true
    const val MINIMUM_TARGET_FLOOR_R: Double = 4.0
    const val MAX_TRADE_RISK_PERCENT: Double = 1.0
    const val MAX_PORTFOLIO_HEAT_PERCENT: Double = 3.0

    /**
     * Verifies immutable launch invariants. Throws IllegalStateException if tampered with.
     */
    fun verifyLaunchInvariants() {
        check(REAL_CAPITAL_AUTHORIZED_USD == 0.00) {
            "CRITICAL SECURITY VIOLATION: Real capital authorization must strictly equal $0.00."
        }
        check(IS_LIVE_TRADING_LOCKED) {
            "CRITICAL SECURITY VIOLATION: Live trading must remain locked."
        }
        check(MINIMUM_TARGET_FLOOR_R >= 4.0) {
            "CRITICAL RISK VIOLATION: Minimum target floor cannot be less than 4.0R."
        }
        check(MAX_TRADE_RISK_PERCENT <= 1.0) {
            "CRITICAL RISK VIOLATION: Maximum trade risk cannot exceed 1.0%."
        }
        check(MAX_PORTFOLIO_HEAT_PERCENT <= 3.0) {
            "CRITICAL RISK VIOLATION: Maximum portfolio heat cannot exceed 3.0%."
        }
    }

    /**
     * Validates whether a proposed order intent is permissible under paper rules.
     * Rejects any order marked as LIVE.
     */
    fun validateOrderIntent(isLive: Boolean, targetR: Double, riskPct: Double): Boolean {
        if (isLive) return false // Live order routing hard-disabled
        if (targetR < MINIMUM_TARGET_FLOOR_R) return false
        if (riskPct > MAX_TRADE_RISK_PERCENT) return false
        return true
    }
}
