package io.cryptoplatform.app.ui.screens

import androidx.compose.foundation.background
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
import io.cryptoplatform.app.ui.components.FinancialCanvasChart
import io.cryptoplatform.app.ui.components.MetricCard
import io.cryptoplatform.app.ui.components.StatusBadge
import io.cryptoplatform.app.ui.theme.*

@Composable
fun BacktestScreen() {
    var selectedAsset by remember { mutableStateOf("BTCUSDT") }
    var selectedSet by remember { mutableStateOf("Set 3 (1D -> 4H -> 1H)") }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BgPage)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        // Backtest Controls
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
                        Text(
                            text = "Backtest Simulation",
                            fontWeight = FontWeight.Bold,
                            fontSize = 15.sp,
                            color = TextPrimary
                        )
                        StatusBadge(
                            text = "HISTORICAL EVIDENCE",
                            backgroundColor = BrandBlue.copy(alpha = 0.1f),
                            textColor = BrandBlue
                        )
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Asset: $selectedAsset • Timeframes: $selectedSet",
                        fontSize = 12.sp,
                        fontFamily = FontFamily.Monospace,
                        color = TextSecondary
                    )
                    Text(
                        text = "Risk: Fixed Fractional (1.00%) • Execution: Closed Candle (Next-Bar Open)",
                        fontSize = 12.sp,
                        fontFamily = FontFamily.Monospace,
                        color = TextSecondary
                    )
                }
            }
        }

        // Metrics Row
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                MetricCard(
                    label = "Win Rate",
                    value = "67.2%",
                    subtext = "9,608 Trades",
                    valueColor = PositiveEmerald,
                    modifier = Modifier.weight(1f)
                )
                MetricCard(
                    label = "Expectancy",
                    value = "+0.8885 R",
                    subtext = "PF: 4.92",
                    valueColor = BrandBlue,
                    modifier = Modifier.weight(1f)
                )
                MetricCard(
                    label = "Max Drawdown",
                    value = "-10.89 R",
                    subtext = "Total: +2,937.4R",
                    valueColor = AlertRed,
                    modifier = Modifier.weight(1f)
                )
            }
        }

        // Equity Curve
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(
                        text = "Historical Cumulative Equity Trajectory",
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp,
                        color = TextPrimary
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Causal deterministic replay (2021–2024). Assumed fees: 4.0 bps, slippage: 2.0 bps.",
                        fontSize = 11.sp,
                        color = TextMuted
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    FinancialCanvasChart(lineColor = PositiveEmerald)
                }
            }
        }
    }
}

@Composable
fun ForwardScreen() {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BgPage)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        // Forward Testing Cohorts
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(
                        text = "Forward Testing Cohorts",
                        fontWeight = FontWeight.Bold,
                        fontSize = 15.sp,
                        color = TextPrimary
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    val cohorts = listOf(
                        Triple("HISTORICAL", "9,608 Trades • Exp: +0.8885R", "CERTIFIED"),
                        Triple("OOS HOLDOUT", "1,665 Trades • Exp: +0.7450R", "VALIDATED"),
                        Triple("PAPER SIMULATION", "Live Continuous Candles", "ACTIVE"),
                        Triple("DEMO GATEWAY", "Binance / Bybit Sandbox", "READY"),
                        Triple("LIVE PRODUCTION", "Authorized Capital: $0.00", "LOCKED ($0)")
                    )

                    cohorts.forEach { (name, desc, status) ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 6.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(name, fontWeight = FontWeight.Bold, fontSize = 13.sp, color = TextPrimary)
                                Text(desc, fontSize = 11.sp, color = TextMuted, fontFamily = FontFamily.Monospace)
                            }
                            StatusBadge(
                                text = status,
                                backgroundColor = if (status.contains("LOCKED")) AlertRed.copy(alpha = 0.1f) else PositiveEmerald.copy(alpha = 0.1f),
                                textColor = if (status.contains("LOCKED")) AlertRed else PositiveEmerald
                            )
                        }
                        Divider(color = BorderLight, thickness = 0.5.dp)
                    }
                }
            }
        }

        // Live Forward Metrics
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(
                        text = "Live Forward Performance Observations",
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp,
                        color = TextPrimary
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(BgSubtle, RoundedCornerShape(4.dp))
                            .padding(10.dp)
                    ) {
                        Text(
                            text = "No forward live observations executed yet. Paper engine is actively observing closed candles without data fabrication.",
                            fontSize = 12.sp,
                            color = TextSecondary
                        )
                    }
                }
            }
        }
    }
}
