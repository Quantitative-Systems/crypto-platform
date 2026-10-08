package io.cryptoplatform.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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
import io.cryptoplatform.app.ui.components.MetricCard
import io.cryptoplatform.app.ui.components.StatusBadge
import io.cryptoplatform.app.ui.theme.*
import io.cryptoplatform.app.ui.viewmodel.MonitoringViewModel
import io.cryptoplatform.app.ui.viewmodel.RiskViewModel
import io.cryptoplatform.app.ui.viewmodel.TradingViewModel

@Composable
fun TradingScreen(viewModel: TradingViewModel) {
    val state by viewModel.uiState.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgPage)
            .padding(16.dp)
    ) {
        // Permanent Safety Lock Banner
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(AlertRed.copy(alpha = 0.08f), RoundedCornerShape(6.dp))
                .padding(12.dp)
        ) {
            Column {
                Text(
                    text = "🔒 LIVE TRADING HARD LOCKED",
                    fontWeight = FontWeight.Bold,
                    fontSize = 13.sp,
                    color = AlertRed
                )
                Text(
                    text = "Real Capital: $0.00. Live order submission is disabled fail-closed across all venues.",
                    fontSize = 11.sp,
                    color = AlertRed.copy(alpha = 0.8f)
                )
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        // Sub Tabs
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            listOf("POSITIONS", "ORDERS", "VENUES").forEach { tab ->
                val isSelected = tab == state.selectedSubTab
                Button(
                    onClick = { viewModel.selectSubTab(tab) },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (isSelected) BrandBlue else BgSurface,
                        contentColor = if (isSelected) Color.White else TextSecondary
                    ),
                    shape = RoundedCornerShape(6.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    Text(tab, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        when (state.selectedSubTab) {
            "POSITIONS" -> {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = BgSurface),
                    shape = RoundedCornerShape(8.dp),
                    border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(24.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "No open positions. Paper engine waiting for closed-candle structural trigger.",
                            fontSize = 12.sp,
                            color = TextMuted,
                            textAlign = androidx.compose.ui.text.style.TextAlign.Center
                        )
                    }
                }
            }
            "ORDERS" -> {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = BgSurface),
                    shape = RoundedCornerShape(8.dp),
                    border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Text(
                            text = "Order Lifecycle Architecture",
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp,
                            color = TextPrimary
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "Signal → Validated → Submitted → Accepted → Filled → Closed → Reconciled",
                            fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace,
                            color = TextMuted
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = "No active orders in paper ledger.",
                            fontSize = 12.sp,
                            color = TextMuted
                        )
                    }
                }
            }
            "VENUES" -> {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(state.venues) { venue ->
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = BgSurface),
                            shape = RoundedCornerShape(8.dp),
                            border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(12.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column {
                                    Text(venue.name, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                    Text("Status: ${venue.status}", fontSize = 11.sp, color = TextMuted)
                                }
                                StatusBadge(
                                    text = if (venue.isLiveLocked) "DEMO / LOCKED" else "ACTIVE",
                                    backgroundColor = BrandBlue.copy(alpha = 0.1f),
                                    textColor = BrandBlue
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun RiskScreen(viewModel: RiskViewModel) {
    val state by viewModel.uiState.collectAsState()
    val m = state.metrics

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BgPage)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        // Invariant Ceilings
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
                        Text("Risk Governance Gauges", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                        StatusBadge("INVARIANTS ACTIVE", PositiveEmerald.copy(alpha = 0.1f), PositiveEmerald)
                    }
                    Spacer(modifier = Modifier.height(10.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        MetricCard(
                            label = "Single Trade Risk",
                            value = "${m.singleTradeRiskPct}%",
                            subtext = "Ceiling <= 1.00%",
                            valueColor = PositiveEmerald,
                            modifier = Modifier.weight(1f)
                        )
                        MetricCard(
                            label = "Portfolio Heat",
                            value = "${m.portfolioHeatPct}0% / 3.00%",
                            subtext = "Ceiling <= 3.00%",
                            valueColor = PositiveEmerald,
                            modifier = Modifier.weight(1f)
                        )
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        MetricCard(
                            label = "Target Floor",
                            value = ">= ${m.targetFloorR}0R",
                            subtext = "Immutable Floor",
                            valueColor = BrandSky,
                            modifier = Modifier.weight(1f)
                        )
                        MetricCard(
                            label = "Drawdown Limit",
                            value = "${m.drawdownPct}0% / ${m.maxDrawdownLimit}0%",
                            subtext = "Max Allowed 5.00%",
                            valueColor = AlertRed,
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
            }
        }

        // Circuit Breakers Card
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text("Circuit Breakers & Halts", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Daily Loss Limit: Armed (Trip threshold 2.50%)", fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                    Text("Consecutive Loss Breaker: Armed (Trip threshold 3 trades)", fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                    Text("Volatility Spike Halt: Armed (Trip threshold >3.0x ATR)", fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                    Text("Reconciliation Mismatch: Fail-Closed Immediate Cancellation", fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                }
            }
        }
    }
}

@Composable
fun MonitoringScreen(viewModel: MonitoringViewModel) {
    val state by viewModel.uiState.collectAsState()
    val h = state.health

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BgPage)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        // System Health Matrix
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text("System Health Matrix", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Spacer(modifier = Modifier.height(8.dp))

                    val items = listOf(
                        "Market Data Feed" to h.marketDataStatus,
                        "Decision Engine" to h.decisionEngineStatus,
                        "Risk Engine" to h.riskEngineStatus,
                        "State Reconciliation" to h.reconciliationStatus,
                        "Strategy Monitoring / Drift" to h.strategyMonitoringStatus,
                        "Forward Testing Engine" to h.forwardTestingStatus,
                        "Live Capital" to h.liveCapitalStatus
                    )

                    items.forEach { (label, status) ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 5.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(label, fontSize = 13.sp, color = TextPrimary)
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

        // Live Alerts
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text("Recent Operational Alerts", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(8.dp))

                    state.alerts.forEach { alert ->
                        Column(modifier = Modifier.padding(vertical = 4.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                StatusBadge(alert.level, PositiveEmerald.copy(alpha = 0.1f), PositiveEmerald)
                                Text(alert.timestamp, fontSize = 10.sp, color = TextMuted, fontFamily = FontFamily.Monospace)
                            }
                            Text(alert.message, fontSize = 12.sp, color = TextSecondary)
                        }
                        Divider(color = BorderLight, thickness = 0.5.dp)
                    }
                }
            }
        }
    }
}

@Composable
fun PerformanceScreen() {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BgPage)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text("Performance Analytics", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(BgSubtle, RoundedCornerShape(4.dp))
                            .padding(12.dp)
                    ) {
                        Text(
                            text = "No observations available. The engine executes causal closed-candle paper simulation with strict historical truthfulness.",
                            fontSize = 12.sp,
                            color = TextSecondary
                        )
                    }
                }
            }
        }
    }
}
