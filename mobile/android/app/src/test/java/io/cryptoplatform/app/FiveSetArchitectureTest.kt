package io.cryptoplatform.app

import io.cryptoplatform.app.domain.model.FiveSetLadder
import io.cryptoplatform.app.domain.model.SevenTimeframeLadder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FiveSetArchitectureTest {

    @Test
    fun testSevenTimeframeLadderCompleteness() {
        val ladder = SevenTimeframeLadder()
        assertEquals(7, ladder.nodes.size)
        val tfs = ladder.nodes.map { it.timeframe }
        val canonical = listOf("1M", "1W", "1D", "4H", "1H", "15M", "3M")
        assertEquals(canonical, tfs)
    }

    @Test
    fun testFiveSetLadderRolesAndEligibility() {
        val ladder = FiveSetLadder("BTCUSDT")
        assertEquals(5, ladder.sets.size)
        assertTrue("Parity must be verified", ladder.parityVerified)

        val set1 = ladder.sets.find { it.setId == "SET_1" }!!
        assertEquals("1M", set1.htfLabel)
        assertEquals("1W", set1.mtfLabel)
        assertEquals("1D", set1.ltfLabel)
        assertFalse("Set 1 is observation only ($0.00 capital)", set1.productionEligible)

        val set2 = ladder.sets.find { it.setId == "SET_2" }!!
        assertEquals("1W", set2.htfLabel)
        assertEquals("1D", set2.mtfLabel)
        assertEquals("4H", set2.ltfLabel)
        assertTrue("Set 2 is production eligible", set2.productionEligible)

        val set3 = ladder.sets.find { it.setId == "SET_3" }!!
        assertEquals("1D", set3.htfLabel)
        assertEquals("4H", set3.mtfLabel)
        assertEquals("1H", set3.ltfLabel)
        assertTrue("Set 3 is production eligible", set3.productionEligible)

        val set4 = ladder.sets.find { it.setId == "SET_4" }!!
        assertEquals("4H", set4.htfLabel)
        assertEquals("1H", set4.mtfLabel)
        assertEquals("15M", set4.ltfLabel)
        assertTrue("Set 4 is production eligible", set4.productionEligible)

        val set5 = ladder.sets.find { it.setId == "SET_5" }!!
        assertEquals("1H", set5.htfLabel)
        assertEquals("15M", set5.mtfLabel)
        assertEquals("3M", set5.ltfLabel)
        assertFalse("Set 5 is observation only ($0.00 capital)", set5.productionEligible)
    }

    @Test
    fun testSharedTimeframeContinuity() {
        val ladder = FiveSetLadder("BTCUSDT")
        val sets = ladder.sets.associateBy { it.setId }

        // Set 1 MTF (1W) == Set 2 HTF (1W)
        assertEquals(sets["SET_1"]!!.mtfLabel, sets["SET_2"]!!.htfLabel)

        // Set 1 LTF (1D) == Set 2 MTF (1D) == Set 3 HTF (1D)
        assertEquals(sets["SET_1"]!!.ltfLabel, sets["SET_2"]!!.mtfLabel)
        assertEquals(sets["SET_2"]!!.mtfLabel, sets["SET_3"]!!.htfLabel)

        // Set 2 LTF (4H) == Set 3 MTF (4H) == Set 4 HTF (4H)
        assertEquals(sets["SET_2"]!!.ltfLabel, sets["SET_3"]!!.mtfLabel)
        assertEquals(sets["SET_3"]!!.mtfLabel, sets["SET_4"]!!.htfLabel)

        // Set 3 LTF (1H) == Set 4 MTF (1H) == Set 5 HTF (1H)
        assertEquals(sets["SET_3"]!!.ltfLabel, sets["SET_4"]!!.mtfLabel)
        assertEquals(sets["SET_4"]!!.mtfLabel, sets["SET_5"]!!.htfLabel)

        // Set 4 LTF (15M) == Set 5 MTF (15M)
        assertEquals(sets["SET_4"]!!.ltfLabel, sets["SET_5"]!!.mtfLabel)
    }
}
