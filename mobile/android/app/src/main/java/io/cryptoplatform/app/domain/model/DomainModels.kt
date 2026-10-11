package io.cryptoplatform.app.domain.model

data class AssetQuote(
    val symbol: String,
    val name: String,
    val price: Double,
    val change24h: Double,
    val marketStructure: String = "Bullish",
    val keyZone: String = "Discount",
    val phase: String = "Pullback",
    val confidence: Int = 72,
    val targetR: Double = 4.2,
    val isPriority: Boolean = false,
    val isWatchlist: Boolean = false
)

data class TimeframeNode(
    val timeframe: String,
    val state: String, // BULL, BEAR, PULL, REV, EXEC
    val isBullish: Boolean
)

data class SevenTimeframeLadder(
    val nodes: List<TimeframeNode> = listOf(
        TimeframeNode("1M", "BULL", true),
        TimeframeNode("1W", "BULL", true),
        TimeframeNode("1D", "BULL", true),
        TimeframeNode("4H", "BULL", true),
        TimeframeNode("1H", "PULL", false),
        TimeframeNode("15M", "REV", true),
        TimeframeNode("3M", "EXEC", true)
    )
)

data class FiveSetEntity(
    val setId: String,
    val name: String,
    val role: String,
    val htfLabel: String,
    val mtfLabel: String,
    val ltfLabel: String,
    val productionEligible: Boolean,
    val purpose: String,
    val sharedTimeframes: List<String> = emptyList()
)

data class FiveSetLadder(
    val symbol: String = "BTCUSDT",
    val sets: List<FiveSetEntity> = listOf(
        FiveSetEntity("SET_1", "Set 1: Macro Context", "Macro Structural Anchor", "1M", "1W", "1D", false, "Regime anchor ($0.00 capital)", listOf("1W", "1D")),
        FiveSetEntity("SET_2", "Set 2: Higher-Timeframe Trading", "Higher-Timeframe Trading", "1W", "1D", "4H", true, "Macro swing trade generation (+1.05R)", listOf("1W", "1D", "4H")),
        FiveSetEntity("SET_3", "Set 3: Daily / Swing Trading", "Daily / Swing Trading", "1D", "4H", "1H", true, "Core swing trade volume (+0.56R)", listOf("1D", "4H", "1H")),
        FiveSetEntity("SET_4", "Set 4: Intraday Trading", "Intraday Trading", "4H", "1H", "15M", true, "High-probability intraday (+0.59R)", listOf("4H", "1H", "15M")),
        FiveSetEntity("SET_5", "Set 5: Lower-Timeframe Observation", "Lower-Timeframe Observation", "1H", "15M", "3M", false, "Entry confirmation anchor ($0.00 capital)", listOf("1H", "15M"))
    ),
    val parityVerified: Boolean = true
)

data class TradeOpportunity(
    val symbol: String,
    val direction: String, // LONG, SHORT
    val phase: String,
    val zone: String,
    val confidence: Int,
    val targetR: Double = 4.0,
    val riskPercent: Double = 1.0,
    val triggerStatus: String = "Closed Candle Confirmed"
)

enum class StrategyStyle {
    SWING,
    INTRADAY,
    SCALPING,
    POSITION,
    SYSTEMATIC,
    RESEARCH
}

enum class ValidationStatus {
    RESEARCH,
    BACKTESTED,
    OOS_VALIDATED,
    FORWARD_TESTING,
    PAPER,
    DEMO,
    PRODUCTION_ELIGIBLE
}

data class StrategyEntity(
    val id: String,
    val name: String,
    val style: StrategyStyle,
    val universe: List<String>,
    val status: ValidationStatus,
    val targetFloorR: Double = 4.0,
    val riskPerTrade: Double = 1.0,
    val historicalTrades: Int = 9608,
    val expectancyR: Double = 0.8885,
    val profitFactor: Double = 4.92,
    val isLiveAuthorized: Boolean = false
)

data class StrategySpec(
    val market: String,
    val style: String,
    val direction: String,
    val marketModel: String = "Multi-Timeframe Structural Model",
    val phase: String = "Pullback to Discount",
    val entryConditions: String = "LTF structural shift confirmation on closed candle",
    val stopConditions: String = "Invalidation below swing anchor",
    val targetConditions: String = ">= 4.00R (Geometric Floor)",
    val riskPerTrade: String = "<= 1.00% Account Equity",
    val timeframeSet: String = "Set 3 (1D -> 4H -> 1H)",
    val validationPlan: String = "Historical Replay (9,608) -> OOS Holdout -> Paper Execution"
)

enum class OrderLifecycleState {
    SIGNAL,
    VALIDATED,
    SUBMITTED,
    ACCEPTED,
    FILLED,
    MANAGED,
    CLOSED,
    RECONCILED
}

data class Order(
    val id: String,
    val timestamp: String,
    val symbol: String,
    val side: String, // BUY, SELL
    val type: String = "LIMIT",
    val price: Double,
    val targetR: Double = 4.0,
    val stopPrice: Double,
    val status: String = "FILLED",
    val lifecycleState: OrderLifecycleState = OrderLifecycleState.RECONCILED
)

data class Position(
    val symbol: String,
    val side: String,
    val entryPrice: Double,
    val currentPrice: Double,
    val size: Double,
    val unrealizedR: Double,
    val pnlUsd: Double,
    val stopLoss: Double,
    val target: Double
)

data class BrokerVenue(
    val id: String,
    val name: String,
    val type: String, // PAPER, TESTNET, DEMO, LIVE
    val status: String,
    val isLiveLocked: Boolean = true
)

data class RiskMetrics(
    val singleTradeRiskPct: Double = 1.00,
    val maxSingleTradeRiskLimit: Double = 1.00,
    val portfolioHeatPct: Double = 0.00,
    val maxPortfolioHeatLimit: Double = 3.00,
    val baseAssetRiskPct: Double = 0.00,
    val maxBaseAssetLimit: Double = 1.00,
    val targetFloorR: Double = 4.00,
    val drawdownPct: Double = 0.00,
    val maxDrawdownLimit: Double = 5.00,
    val dailyLossBreakerArmed: Boolean = true,
    val consecutiveLossBreakerArmed: Boolean = true,
    val volatilitySpikeBreakerArmed: Boolean = true,
    val realCapitalAuthorizedUsd: Double = 0.00
)

data class SystemHealth(
    val marketDataStatus: String = "CONNECTED",
    val decisionEngineStatus: String = "RUNNING",
    val riskEngineStatus: String = "NORMAL",
    val reconciliationStatus: String = "0 DISCREPANCIES",
    val strategyMonitoringStatus: String = "NORMAL",
    val forwardTestingStatus: String = "ACTIVE",
    val liveCapitalStatus: String = "$0.00 LOCKED"
)

data class AlertItem(
    val id: String,
    val timestamp: String,
    val level: String, // INFO, WARNING, CRITICAL
    val title: String,
    val message: String
)

data class BacktestBenchmark(
    val unfilteredTrades: Int = 9608,
    val unfilteredExpectancyR: Double = 0.5781,
    val unfilteredProfitFactor: Double = 2.352,
    val unfilteredWinRate: Double = 0.493,
    val totalTrades: Int = 2942,
    val sampleSizeFiltered: Int = 2942,
    val confidenceThreshold: String = ">= 0.60",
    val expectancyR: Double = 0.8885,
    val profitFactor: Double = 4.918,
    val winRate: Double = 0.672,
    val maxDrawdownR: Double = 10.89,
    val tailRiskCvar: Double = 1.284,
    val targetFloor: String = ">= 4.0R",
    val status: String = "PROTECTED_BASELINE"
)

data class BacktestRunItem(
    val id: String,
    val strategy: String,
    val symbol: String,
    val timeframes: List<String>,
    val trades: Int,
    val expectancyR: Double,
    val profitFactor: Double,
    val winRate: Double,
    val maxDrawdownR: Double,
    val environment: String
)

data class BacktestReport(
    val benchmark: BacktestBenchmark = BacktestBenchmark(),
    val recentRuns: List<BacktestRunItem> = emptyList()
)

data class EnvironmentValidation(
    val name: String,
    val tradesEvaluated: Int,
    val expectancyR: Double = 0.0,
    val profitFactor: Double = 0.0,
    val winRate: Double = 0.0,
    val maxDrawdownR: Double = 0.0,
    val status: String,
    val provenance: String
)

data class ForwardValidationReport(
    val environments: List<EnvironmentValidation> = emptyList(),
    val realCapitalAuthorized: Double = 0.00,
    val minTargetR: Double = 4.0,
    val maxTradeRiskPct: Double = 1.0,
    val maxPortfolioHeatPct: Double = 3.0
)

data class PerformanceTelemetry(
    val uptimeSeconds: Long = 0L,
    val memoryUsageMb: Double = 0.0,
    val eventLoopLagMs: Double = 0.0,
    val openPositionsCount: Int = 0,
    val closedPositionsCount: Int = 0,
    val totalOrdersCount: Int = 0,
    val decisionsCount: Int = 0,
    val executionMode: String = "PAPER",
    val realCapitalAuthorized: Double = 0.00
)

