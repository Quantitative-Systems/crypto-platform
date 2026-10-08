package io.cryptoplatform.app.ui.navigation

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
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
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import io.cryptoplatform.app.core.network.CryptoApiClient
import io.cryptoplatform.app.data.repository.*
import io.cryptoplatform.app.ui.components.EmergencyStopDialog
import io.cryptoplatform.app.ui.components.StatusBadge
import io.cryptoplatform.app.ui.screens.*
import io.cryptoplatform.app.ui.theme.*
import io.cryptoplatform.app.ui.viewmodel.*
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CryptoPlatformAppRoot(
    navController: NavHostController = rememberNavController()
) {
    val api = remember { CryptoApiClient() }
    val marketRepo = remember { MarketRepository(api) }
    val strategyRepo = remember { StrategyRepository(api) }
    val tradingRepo = remember { TradingRepository(api) }
    val riskRepo = remember { RiskRepository(api) }
    val monitoringRepo = remember { MonitoringRepository(api) }
    val authRepo = remember { AuthRepository(api) }

    val homeViewModel = remember { HomeViewModel(marketRepo) }
    val marketsViewModel = remember { MarketsViewModel(marketRepo) }
    val strategiesViewModel = remember { StrategiesViewModel(strategyRepo) }
    val researchViewModel = remember { ResearchViewModel(strategyRepo) }
    val tradingViewModel = remember { TradingViewModel(tradingRepo) }
    val riskViewModel = remember { RiskViewModel(riskRepo) }
    val monitoringViewModel = remember { MonitoringViewModel(monitoringRepo) }
    val accountViewModel = remember { AccountViewModel(authRepo) }

    var isEmergencyStopOpen by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route ?: NavRoute.Home.route

    Scaffold(
        topBar = {
            Column {
                // Main Header
                TopAppBar(
                    title = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = "Crypto Platform",
                                fontWeight = FontWeight.Bold,
                                fontSize = 16.sp,
                                color = TextPrimary
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            StatusBadge(
                                text = "PAPER",
                                backgroundColor = BrandBlue.copy(alpha = 0.1f),
                                textColor = BrandBlue
                            )
                        }
                    },
                    actions = {
                        Text(
                            text = "$0 CAPITAL",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            color = PositiveEmerald
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Button(
                            onClick = { isEmergencyStopOpen = true },
                            colors = ButtonDefaults.buttonColors(containerColor = AlertRed.copy(alpha = 0.1f)),
                            shape = RoundedCornerShape(6.dp),
                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                            border = ButtonDefaults.outlinedButtonBorder.copy(brush = androidx.compose.ui.graphics.SolidColor(AlertRed.copy(alpha = 0.3f)))
                        ) {
                            Text("🛑 STOP", color = AlertRed, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = BgSurface)
                )

                // Horizontal Sub-Tabs Row for quick access across all 11 modules
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(BgSurface)
                        .horizontalScroll(rememberScrollState())
                        .padding(horizontal = 12.dp, vertical = 4.dp),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    NavRoute.allSections.forEach { section ->
                        val isSelected = currentRoute == section.route
                        Box(
                            modifier = Modifier
                                .background(
                                    if (isSelected) BrandBlue else BgPage,
                                    RoundedCornerShape(6.dp)
                                )
                                .border(1.dp, if (isSelected) BrandBlue else BorderLight, RoundedCornerShape(6.dp))
                                .clickable { navController.navigate(section.route) }
                                .padding(horizontal = 10.dp, vertical = 5.dp)
                        ) {
                            Text(
                                text = section.title,
                                color = if (isSelected) Color.White else TextMuted,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }
                }
                Divider(color = BorderLight, thickness = 1.dp)
            }
        },
        bottomBar = {
            NavigationBar(
                containerColor = BgSurface,
                tonalElevation = 0.dp
            ) {
                NavRoute.bottomNavItems.forEach { item ->
                    val isSelected = currentRoute == item.route
                    NavigationBarItem(
                        selected = isSelected,
                        onClick = { navController.navigate(item.route) },
                        icon = { Text(item.icon, fontSize = 18.sp) },
                        label = { Text(item.title, fontSize = 10.sp, fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = BrandBlue,
                            selectedTextColor = BrandBlue,
                            unselectedIconColor = TextMuted,
                            unselectedTextColor = TextMuted,
                            indicatorColor = Color.Transparent
                        )
                    )
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = NavRoute.Home.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(NavRoute.Home.route) {
                HomeScreen(
                    viewModel = homeViewModel,
                    onNavigateToMarkets = { navController.navigate(NavRoute.Markets.route) },
                    onNavigateToDetail = { sym -> navController.navigate(NavRoute.MarketDetail.createRoute(sym)) }
                )
            }
            composable(NavRoute.Markets.route) {
                MarketsScreen(
                    viewModel = marketsViewModel,
                    onNavigateToDetail = { sym -> navController.navigate(NavRoute.MarketDetail.createRoute(sym)) }
                )
            }
            composable(NavRoute.MarketDetail.route) { backStack ->
                val sym = backStack.arguments?.getString("symbol") ?: "BTCUSDT"
                val detailViewModel = remember(sym) { MarketDetailViewModel(marketRepo, sym) }
                MarketDetailScreen(
                    viewModel = detailViewModel,
                    onBack = { navController.popBackStack() }
                )
            }
            composable(NavRoute.Strategies.route) {
                StrategiesScreen(
                    viewModel = strategiesViewModel,
                    onNavigateToBacktest = { navController.navigate(NavRoute.Backtesting.route) }
                )
            }
            composable(NavRoute.Research.route) {
                ResearchScreen(
                    viewModel = researchViewModel,
                    onNavigateToBacktest = { navController.navigate(NavRoute.Backtesting.route) }
                )
            }
            composable(NavRoute.Backtesting.route) {
                BacktestScreen()
            }
            composable(NavRoute.ForwardTesting.route) {
                ForwardScreen()
            }
            composable(NavRoute.Trading.route) {
                TradingScreen(viewModel = tradingViewModel)
            }
            composable(NavRoute.Risk.route) {
                RiskScreen(viewModel = riskViewModel)
            }
            composable(NavRoute.Performance.route) {
                PerformanceScreen()
            }
            composable(NavRoute.Monitoring.route) {
                MonitoringScreen(viewModel = monitoringViewModel)
            }
            composable(NavRoute.Account.route) {
                AccountScreen(
                    viewModel = accountViewModel,
                    onTriggerEmergencyStop = { isEmergencyStopOpen = true }
                )
            }
        }

        // Global Emergency Stop Confirmation Dialog
        EmergencyStopDialog(
            isOpen = isEmergencyStopOpen,
            onDismiss = { isEmergencyStopOpen = false },
            onConfirm = {
                isEmergencyStopOpen = false
                scope.launch {
                    tradingRepo.emergencyHalt()
                }
            }
        )
    }
}
