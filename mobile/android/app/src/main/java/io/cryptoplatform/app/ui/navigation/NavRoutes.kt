package io.cryptoplatform.app.ui.navigation

sealed class NavRoute(val route: String, val title: String, val icon: String) {
    object Home : NavRoute("home", "Home", "📊")
    object Markets : NavRoute("markets", "Markets", "📈")
    object MarketDetail : NavRoute("market_detail/{symbol}", "Market Detail", "🔍") {
        fun createRoute(symbol: String) = "market_detail/$symbol"
    }
    object Strategies : NavRoute("strategies", "Strategies", "📚")
    object Research : NavRoute("research", "Research", "✨")
    object Backtesting : NavRoute("backtest", "Backtest", "🧪")
    object ForwardTesting : NavRoute("forward", "Forward", "⏱️")
    object Trading : NavRoute("trading", "Trading", "⚡")
    object Risk : NavRoute("risk", "Risk", "🛡️")
    object Performance : NavRoute("performance", "Performance", "📈")
    object Monitoring : NavRoute("monitoring", "Monitoring", "📡")
    object Account : NavRoute("account", "Account", "⚙️")

    companion object {
        val bottomNavItems = listOf(Home, Markets, Strategies, Research, Trading, Account)
        val allSections = listOf(Home, Markets, Strategies, Research, Backtesting, ForwardTesting, Trading, Risk, Performance, Monitoring, Account)
    }
}
