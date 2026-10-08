package io.cryptoplatform.app

import io.cryptoplatform.app.core.security.CapitalSafetyGate
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CapitalSafetyTest {

    @Test
    fun testRealCapitalIsZero() {
        assertEquals("Real capital authorized must be exactly 0.0", 0.00, CapitalSafetyGate.REAL_CAPITAL_AUTHORIZED_USD, 0.0001)
    }

    @Test
    fun testLiveTradingIsLocked() {
        assertTrue("Live trading must remain locked", CapitalSafetyGate.IS_LIVE_TRADING_LOCKED)
    }

    @Test
    fun testVerifyLaunchInvariantsPasses() {
        CapitalSafetyGate.verifyLaunchInvariants()
    }

    @Test
    fun testLiveOrderIntentRejected() {
        val result = CapitalSafetyGate.validateOrderIntent(isLive = true, targetR = 4.5, riskPct = 0.5)
        assertFalse("Live order intent must always be rejected", result)
    }

    @Test
    fun testPaperOrderValidation() {
        val valid = CapitalSafetyGate.validateOrderIntent(isLive = false, targetR = 4.5, riskPct = 0.5)
        assertTrue("Valid paper order must be accepted", valid)

        val sub4R = CapitalSafetyGate.validateOrderIntent(isLive = false, targetR = 3.5, riskPct = 0.5)
        assertFalse("Sub-4R order must be rejected", sub4R)

        val excessRisk = CapitalSafetyGate.validateOrderIntent(isLive = false, targetR = 4.5, riskPct = 1.5)
        assertFalse("Excess risk order must be rejected", excessRisk)
    }

    @Test
    fun testInvariantsConstants() {
        assertEquals(4.0, CapitalSafetyGate.MINIMUM_TARGET_FLOOR_R, 0.0001)
        assertEquals(1.0, CapitalSafetyGate.MAX_TRADE_RISK_PERCENT, 0.0001)
        assertEquals(3.0, CapitalSafetyGate.MAX_PORTFOLIO_HEAT_PERCENT, 0.0001)
    }
}
