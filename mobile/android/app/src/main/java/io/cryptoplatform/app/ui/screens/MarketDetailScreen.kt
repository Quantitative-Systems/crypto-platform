package io.cryptoplatform.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import io.cryptoplatform.app.domain.model.FiveSetLadder
import io.cryptoplatform.app.ui.components.FinancialCanvasChart
import io.cryptoplatform.app.ui.components.SevenTimeframeLadderView
import io.cryptoplatform.app.ui.components.StatusBadge
import io.cryptoplatform.app.ui.theme.*
import io.cryptoplatform.app.ui.viewmodel.MarketDetailViewModel

@Composable
fun MarketDetailScreen(
    viewModel: MarketDetailViewModel,
    onBack: () -> Unit
) {
    val state by viewModel.uiState.collectAsState()
    val quote = state.quote

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BgPage)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        // Back Button & Asset Header
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedButton(
                    onClick = onBack,
                    shape = RoundedCornerShape(6.dp),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                ) {
                    Text("← Markets", fontSize = 12.sp, color = TextPrimary)
                }
                StatusBadge(
                    text = "ADMITTED UNIVERSE",
                    backgroundColor = BrandBlue.copy(alpha = 0.1f),
                    textColor = BrandBlue
                )
            }
        }

        // Price & Structure Card
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(
                                text = state.symbol,
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = TextPrimary
                            )
                            if (state.isStreamingConnected) {
                                StatusBadge(
                                    text = "LIVE WS #${state.lastEventSequence}",
                                    backgroundColor = PositiveEmerald.copy(alpha = 0.15f),
                                    textColor = PositiveEmerald
                                )
                            } else {
                                StatusBadge(
                                    text = if (state.isDataStale) "STALE / RECONNECTING" else "CONNECTING",
                                    backgroundColor = AlertRed.copy(alpha = 0.15f),
                                    textColor = AlertRed
                                )
                            }
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text(
                                text = "$${String.format("%,.2f", quote?.price ?: 64850.0)}",
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace,
                                color = TextPrimary
                            )
                            Text(
                                text = "${if ((quote?.change24h ?: 0.0) >= 0) "+" else ""}${quote?.change24h ?: 2.45}% (24h)",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = if ((quote?.change24h ?: 0.0) >= 0) PositiveEmerald else AlertRed,
                                fontFamily = FontFamily.Monospace
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    // Timeframe Selector Buttons
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        listOf("1M", "1W", "1D", "4H", "1H", "15M", "3M").forEach { tf ->
                            val isSelected = tf == state.selectedTimeframe
                            Box(
                                modifier = Modifier
                                    .background(
                                        if (isSelected) BrandBlue else BgSubtle,
                                        RoundedCornerShape(4.dp)
                                    )
                                    .clickable { viewModel.selectTimeframe(tf) }
                                    .padding(horizontal = 8.dp, vertical = 4.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = tf,
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (isSelected) Color.White else TextMuted,
                                    fontFamily = FontFamily.Monospace
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    // Interactive Financial Chart
                    FinancialCanvasChart()

                    Spacer(modifier = Modifier.height(10.dp))

                    Text(
                        text = "Seven-Timeframe Multi-Scale Ladder",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TextMuted,
                        fontFamily = FontFamily.Monospace
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    SevenTimeframeLadderView(ladder = state.ladder)
                }
            }
        }

        // Structural State Card
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(
                        text = "Market Intelligence Matrix",
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp,
                        color = TextPrimary
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .background(BgSubtle, RoundedCornerShape(6.dp))
                                .padding(8.dp)
                        ) {
                            Column {
                                Text("STRUCTURE", fontSize = 10.sp, color = TextMuted, fontFamily = FontFamily.Monospace)
                                Text("Bullish", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = PositiveEmerald)
                            }
                        }
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .background(BgSubtle, RoundedCornerShape(6.dp))
                                .padding(8.dp)
                        ) {
                            Column {
                                Text("KEY ZONE", fontSize = 10.sp, color = TextMuted, fontFamily = FontFamily.Monospace)
                                Text("Discount", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandSky)
                            }
                        }
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .background(BgSubtle, RoundedCornerShape(6.dp))
                                .padding(8.dp)
                        ) {
                            Column {
                                Text("PHASE", fontSize = 10.sp, color = TextMuted, fontFamily = FontFamily.Monospace)
                                Text("Pullback", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = WarningAmber)
                            }
                        }
                    }
                }
            }
        }

        // Five-Set Overlapping Ladder & Parity Card
        item {
            FiveSetLadderCard(ladder = state.fiveSetLadder)
        }

        // Simulated Paper Order Action
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(
                        text = "Simulated Order Execution",
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp,
                        color = TextPrimary
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Target Floor: >= 4.00R • Risk: <= 1.00% • Closed-Candle Trigger",
                        fontSize = 12.sp,
                        color = TextSecondary,
                        fontFamily = FontFamily.Monospace
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            onClick = { viewModel.simulatePaperOrder("BUY") },
                            colors = ButtonDefaults.buttonColors(containerColor = PositiveEmerald),
                            shape = RoundedCornerShape(6.dp),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Paper Buy", color = Color.White, fontWeight = FontWeight.Bold)
                        }
                        Button(
                            onClick = { viewModel.simulatePaperOrder("SELL") },
                            colors = ButtonDefaults.buttonColors(containerColor = AlertRed),
                            shape = RoundedCornerShape(6.dp),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Paper Sell", color = Color.White, fontWeight = FontWeight.Bold)
                        }
                    }

                    state.orderMessage?.let { msg ->
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = msg,
                            color = BrandBlue,
                            fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun FiveSetLadderCard(ladder: FiveSetLadder) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = BgSurface),
        shape = RoundedCornerShape(8.dp),
        border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Five-Set Overlapping Ladder",
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp,
                    color = TextPrimary
                )
                StatusBadge(
                    text = if (ladder.parityVerified) "PARITY: VERIFIED" else "PARITY: PENDING",
                    backgroundColor = PositiveEmerald.copy(alpha = 0.1f),
                    textColor = PositiveEmerald
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
            for (s in ladder.sets) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1.5f)) {
                        Text(s.name, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                        Text(
                            "${s.htfLabel} (HTF) → ${s.mtfLabel} (MTF) → ${s.ltfLabel} (LTF)",
                            fontSize = 10.sp,
                            color = TextMuted,
                            fontFamily = FontFamily.Monospace
                        )
                    }
                    StatusBadge(
                        text = if (s.productionEligible) "PROD ELIGIBLE" else "$0.00 OBS ONLY",
                        backgroundColor = if (s.productionEligible) BrandBlue.copy(alpha = 0.1f) else AlertRed.copy(alpha = 0.1f),
                        textColor = if (s.productionEligible) BrandBlue else AlertRed
                    )
                }
            }
        }
    }
}
