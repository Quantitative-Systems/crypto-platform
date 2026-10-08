package io.cryptoplatform.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import io.cryptoplatform.app.domain.model.AssetQuote
import io.cryptoplatform.app.ui.components.MetricCard
import io.cryptoplatform.app.ui.components.StatusBadge
import io.cryptoplatform.app.ui.theme.*
import io.cryptoplatform.app.ui.viewmodel.HomeViewModel
import io.cryptoplatform.app.ui.viewmodel.MarketsViewModel

@Composable
fun HomeScreen(
    viewModel: HomeViewModel,
    onNavigateToMarkets: () -> Unit,
    onNavigateToDetail: (String) -> Unit
) {
    val state by viewModel.uiState.collectAsState()

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BgPage)
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
        contentPadding = PaddingValues(top = 12.dp, bottom = 24.dp)
    ) {
        // 1. Portfolio Card
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(
                        text = "PORTFOLIO EQUITY",
                        color = TextMuted,
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "$100,000.00",
                        color = TextPrimary,
                        fontSize = 26.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        StatusBadge(
                            text = "PAPER / DEMO",
                            backgroundColor = BrandBlue.copy(alpha = 0.1f),
                            textColor = BrandBlue
                        )
                        Text(
                            text = "Today's P&L: —",
                            color = TextMuted,
                            fontSize = 12.sp,
                            fontFamily = FontFamily.Monospace
                        )
                    }
                }
            }
        }

        // 2. Risk Metrics Row
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                MetricCard(
                    label = "Portfolio Heat",
                    value = "${state.portfolioHeatPct}0% / 3.00%",
                    subtext = "Hard Limit <= 3.00%",
                    valueColor = PositiveEmerald,
                    modifier = Modifier.weight(1f)
                )
                MetricCard(
                    label = "Single Trade Risk",
                    value = "1.00%",
                    subtext = "Hard Ceiling <= 1.00%",
                    valueColor = BrandSky,
                    modifier = Modifier.weight(1f)
                )
            }
        }

        // 3. Markets Quick List
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Admitted Markets",
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                            color = TextPrimary
                        )
                        Text(
                            text = "View All →",
                            color = BrandBlue,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.clickable { onNavigateToMarkets() }
                        )
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    state.markets.take(4).forEach { quote ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { onNavigateToDetail(quote.symbol) }
                                .padding(vertical = 6.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(
                                        text = quote.symbol,
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 13.sp,
                                        color = TextPrimary
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    StatusBadge(
                                        text = quote.marketStructure,
                                        backgroundColor = PositiveEmerald.copy(alpha = 0.1f),
                                        textColor = PositiveEmerald
                                    )
                                }
                                Text(
                                    text = "${quote.phase} to ${quote.keyZone}",
                                    color = TextMuted,
                                    fontSize = 11.sp
                                )
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                Text(
                                    text = "$${String.format("%,.2f", quote.price)}",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 13.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = TextPrimary
                                )
                                Text(
                                    text = "${if (quote.change24h >= 0) "+" else ""}${quote.change24h}%",
                                    color = if (quote.change24h >= 0) PositiveEmerald else AlertRed,
                                    fontWeight = FontWeight.SemiBold,
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace
                                )
                            }
                        }
                        Divider(color = BorderLight, thickness = 0.5.dp)
                    }
                }
            }
        }

        // 4. Trade Opportunity Card
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Trade Opportunities",
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                            color = TextPrimary
                        )
                        StatusBadge(
                            text = "TARGET >= 4R",
                            backgroundColor = BrandSky.copy(alpha = 0.1f),
                            textColor = BrandSky
                        )
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "BTCUSDT • Bullish / Pullback",
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 13.sp,
                        color = TextPrimary
                    )
                    Text(
                        text = "Confidence: 72% • Target Floor: >= 4.0R • Risk: <= 1.0%",
                        color = TextSecondary,
                        fontSize = 12.sp,
                        fontFamily = FontFamily.Monospace
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Causal closed-candle trigger verified. Simulated execution ready.",
                        color = TextMuted,
                        fontSize = 11.sp
                    )
                }
            }
        }

        // 5. System Status Strip
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "System Status",
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                            color = TextPrimary
                        )
                        StatusBadge(
                            text = "NORMAL",
                            backgroundColor = PositiveEmerald.copy(alpha = 0.1f),
                            textColor = PositiveEmerald
                        )
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Mode: Paper Trading • Live Capital: $0.00 (LOCKED)",
                        color = TextSecondary,
                        fontSize = 12.sp,
                        fontFamily = FontFamily.Monospace
                    )
                    Text(
                        text = "Reconciliation: 0 Discrepancies • Decision Engine: Running",
                        color = TextSecondary,
                        fontSize = 12.sp,
                        fontFamily = FontFamily.Monospace
                    )
                }
            }
        }
    }
}

@Composable
fun MarketsScreen(
    viewModel: MarketsViewModel,
    onNavigateToDetail: (String) -> Unit
) {
    val state by viewModel.uiState.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgPage)
            .padding(16.dp)
    ) {
        // Filter Buttons & Search
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Button(
                onClick = { viewModel.setFilter("ALL") },
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (state.filterType == "ALL") BrandBlue else BgSurface,
                    contentColor = if (state.filterType == "ALL") Color.White else TextSecondary
                ),
                shape = RoundedCornerShape(6.dp),
                modifier = Modifier.weight(1f)
            ) {
                Text("All Admitted", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
            }
            Button(
                onClick = { viewModel.setFilter("WATCHLIST") },
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (state.filterType == "WATCHLIST") BrandBlue else BgSurface,
                    contentColor = if (state.filterType == "WATCHLIST") Color.White else TextSecondary
                ),
                shape = RoundedCornerShape(6.dp),
                modifier = Modifier.weight(1f)
            ) {
                Text("Watchlist / Priority", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        OutlinedTextField(
            value = state.searchQuery,
            onValueChange = { viewModel.setSearch(it) },
            placeholder = { Text("Search assets (e.g. BTC, ETH)...", fontSize = 13.sp) },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(6.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = BgSurface,
                unfocusedContainerColor = BgSurface,
                focusedBorderColor = BrandBlue,
                unfocusedBorderColor = BorderLight
            )
        )

        Spacer(modifier = Modifier.height(12.dp))

        val filteredList = state.assets.filter {
            (state.filterType == "ALL" || it.isWatchlist) &&
            (it.symbol.contains(state.searchQuery, ignoreCase = true) || it.name.contains(state.searchQuery, ignoreCase = true))
        }

        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(filteredList) { quote ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onNavigateToDetail(quote.symbol) },
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
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(
                                    text = quote.symbol,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp,
                                    color = TextPrimary
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                StatusBadge(
                                    text = quote.marketStructure,
                                    backgroundColor = PositiveEmerald.copy(alpha = 0.1f),
                                    textColor = PositiveEmerald
                                )
                            }
                            Text(
                                text = "${quote.name} • ${quote.phase}",
                                color = TextMuted,
                                fontSize = 11.sp
                            )
                        }

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(horizontalAlignment = Alignment.End) {
                                Text(
                                    text = "$${String.format("%,.2f", quote.price)}",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = TextPrimary
                                )
                                Text(
                                    text = "${if (quote.change24h >= 0) "+" else ""}${quote.change24h}%",
                                    color = if (quote.change24h >= 0) PositiveEmerald else AlertRed,
                                    fontWeight = FontWeight.SemiBold,
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace
                                )
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Text(
                                text = if (quote.isWatchlist) "⭐" else "☆",
                                fontSize = 18.sp,
                                modifier = Modifier.clickable { viewModel.toggleWatchlist(quote.symbol) }
                            )
                        }
                    }
                }
            }
        }
    }
}
