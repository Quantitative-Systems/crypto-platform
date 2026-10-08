package io.cryptoplatform.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import io.cryptoplatform.app.ui.components.StatusBadge
import io.cryptoplatform.app.ui.theme.*
import io.cryptoplatform.app.ui.viewmodel.ResearchViewModel
import io.cryptoplatform.app.ui.viewmodel.StrategiesViewModel

@Composable
fun StrategiesScreen(
    viewModel: StrategiesViewModel,
    onNavigateToBacktest: () -> Unit
) {
    val state by viewModel.uiState.collectAsState()
    val styles = listOf("ALL", "SWING", "INTRADAY", "SCALPING", "POSITION", "SYSTEMATIC", "RESEARCH")

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgPage)
            .padding(16.dp)
    ) {
        // Style Filters
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            styles.take(4).forEach { style ->
                val isSelected = style == state.selectedStyle
                Button(
                    onClick = { viewModel.selectStyle(style) },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (isSelected) BrandBlue else BgSurface,
                        contentColor = if (isSelected) Color.White else TextSecondary
                    ),
                    shape = RoundedCornerShape(6.dp),
                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    Text(style, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            items(state.strategies) { strat ->
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
                                text = strat.name,
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp,
                                color = TextPrimary
                            )
                            StatusBadge(
                                text = strat.status.name.replace("_", " "),
                                backgroundColor = BrandBlue.copy(alpha = 0.1f),
                                textColor = BrandBlue
                            )
                        }
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = "Style: ${strat.style.name} • Universe: ${strat.universe.joinToString(", ")}",
                            fontSize = 12.sp,
                            color = TextMuted
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = "Target Floor: >= ${strat.targetFloorR}R",
                                fontSize = 12.sp,
                                fontFamily = FontFamily.Monospace,
                                color = TextSecondary
                            )
                            Text(
                                text = "Risk: <= ${strat.riskPerTrade}%",
                                fontSize = 12.sp,
                                fontFamily = FontFamily.Monospace,
                                color = TextSecondary
                            )
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "Historical Replay: ${strat.historicalTrades} Trades • PF: ${strat.profitFactor} • Exp: +${strat.expectancyR}R",
                            fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace,
                            color = PositiveEmerald
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Divider(color = BorderLight, thickness = 0.5.dp)
                        Spacer(modifier = Modifier.height(6.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Live Trading: Not Authorized ($0)",
                                fontSize = 11.sp,
                                color = AlertRed,
                                fontWeight = FontWeight.SemiBold
                            )
                            Text(
                                text = "View Backtest →",
                                fontSize = 12.sp,
                                color = BrandBlue,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.clickable { onNavigateToBacktest() }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ResearchScreen(
    viewModel: ResearchViewModel,
    onNavigateToBacktest: () -> Unit
) {
    val state by viewModel.uiState.collectAsState()

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BgPage)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        // Research Prompt Card
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
                            text = "Research Assistant",
                            fontWeight = FontWeight.Bold,
                            fontSize = 15.sp,
                            color = TextPrimary
                        )
                        StatusBadge(
                            text = "NATURAL LANGUAGE",
                            backgroundColor = BrandSky.copy(alpha = 0.1f),
                            textColor = BrandSky
                        )
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Formulate quantitative hypotheses. The system parses structural conditions and guarantees >=4R target floor invariants.",
                        fontSize = 12.sp,
                        color = TextMuted
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    OutlinedTextField(
                        value = state.prompt,
                        onValueChange = { viewModel.updatePrompt(it) },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 3,
                        shape = RoundedCornerShape(6.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = BgSurface,
                            unfocusedContainerColor = BgSurface,
                            focusedBorderColor = BrandBlue,
                            unfocusedBorderColor = BorderLight
                        )
                    )

                    Spacer(modifier = Modifier.height(10.dp))

                    Button(
                        onClick = { viewModel.parsePrompt() },
                        colors = ButtonDefaults.buttonColors(containerColor = BrandBlue),
                        shape = RoundedCornerShape(6.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            if (state.isParsing) "Parsing Specification..." else "✨ Generate Specification",
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }

        // Specification Output
        state.specification?.let { spec ->
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
                                text = "Structured Specification",
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp,
                                color = TextPrimary
                            )
                            StatusBadge(
                                text = "HYPOTHESIS",
                                backgroundColor = PositiveEmerald.copy(alpha = 0.1f),
                                textColor = PositiveEmerald
                            )
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("MARKET: ${spec.market}", fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                        Text("STYLE: ${spec.style}", fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                        Text("DIRECTION: ${spec.direction}", fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                        Text("MODEL: ${spec.marketModel}", fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                        Text("TARGET: ${spec.targetConditions}", fontSize = 12.sp, fontFamily = FontFamily.Monospace, color = BrandBlue)
                        Text("RISK: ${spec.riskPerTrade}", fontSize = 12.sp, fontFamily = FontFamily.Monospace, color = PositiveEmerald)
                        Text("PLAN: ${spec.validationPlan}", fontSize = 12.sp, fontFamily = FontFamily.Monospace)

                        Spacer(modifier = Modifier.height(10.dp))
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(AlertRed.copy(alpha = 0.08f), RoundedCornerShape(4.dp))
                                .padding(8.dp)
                        ) {
                            Text(
                                text = "RESEARCH NOTICE: The system models market state and executes deterministic rules. Past performance does not guarantee future results.",
                                fontSize = 11.sp,
                                color = AlertRed,
                                fontWeight = FontWeight.SemiBold
                            )
                        }

                        Spacer(modifier = Modifier.height(10.dp))
                        Button(
                            onClick = onNavigateToBacktest,
                            colors = ButtonDefaults.buttonColors(containerColor = BrandBlue),
                            shape = RoundedCornerShape(6.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Run Backtest on Hypothesis →", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
    }
}
