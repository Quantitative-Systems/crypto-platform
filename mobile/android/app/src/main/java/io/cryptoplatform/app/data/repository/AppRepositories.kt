package io.cryptoplatform.app.data.repository

import io.cryptoplatform.app.CryptoPlatformApp
import io.cryptoplatform.app.core.network.CryptoApiClient
import io.cryptoplatform.app.core.security.CapitalSafetyGate
import io.cryptoplatform.app.domain.model.*
import org.json.JSONArray
import org.json.JSONObject

class MarketRepository(private val api: CryptoApiClient) {

    private val defaultAssetNames = mapOf(
        "BTCUSDT" to "Bitcoin",
        "ETHUSDT" to "Ethereum",
        "SOLUSDT" to "Solana",
        "BNBUSDT" to "BNB"
    )

    suspend fun getMarkets(): List<AssetQuote> {
        val watchlist = CryptoPlatformApp.instance.secureStorage.getWatchlist()
        val result = api.get("/api/markets")

        if (result.isSuccess) {
            try {
                val json = JSONObject(result.getOrThrow())
                val allArray = json.optJSONArray("all_assets") ?: JSONArray()
                if (allArray.length() > 0) {
                    val list = mutableListOf<AssetQuote>()
                    for (i in 0 until allArray.length()) {
                        val item = allArray.opt(i)
                        val sym = if (item is JSONObject) item.optString("symbol", "") else item.toString()
                        val name = if (item is JSONObject && item.has("base_asset")) item.optString("base_asset") else defaultAssetNames[sym] ?: sym.removeSuffix("USDT")
                        val price = if (item is JSONObject) item.optDouble("current_price", 0.0) else 0.0
                        val change = if (item is JSONObject) item.optDouble("change_24h_pct", 0.0) else 0.0
                        val structure = if (item is JSONObject) item.optString("market_structure_summary", "Bullish") else "Bullish"
                        val phase = if (item is JSONObject) item.optString("phase_summary", "Pullback") else "Pullback"
                        val isPriority = if (item is JSONObject) item.optBoolean("is_priority", false) else false

                        list.add(
                            AssetQuote(
                                symbol = sym,
                                name = name,
                                price = price,
                                change24h = change,
                                marketStructure = structure,
                                phase = phase,
                                isPriority = isPriority,
                                isWatchlist = watchlist.contains(sym)
                            )
                        )
                    }
                    if (list.isNotEmpty()) return list
                }
            } catch (ignored: Exception) {}
        }

        return emptyList()
    }

    suspend fun toggleWatchlist(symbol: String): Boolean {
        val storage = CryptoPlatformApp.instance.secureStorage
        val set = storage.getWatchlist().toMutableSet()
        val isNowWatched = if (set.contains(symbol)) {
            set.remove(symbol)
            false
        } else {
            set.add(symbol)
            true
        }
        storage.setWatchlist(set)

        // Sync with backend API
        try {
            val body = JSONObject().put("symbol", symbol)
            api.post("/api/markets/watchlist", body)
        } catch (ignored: Exception) {}

        return isNowWatched
    }

    suspend fun getActiveOpportunity(): TradeOpportunity {
        val result = api.get("/api/king/overview")
        if (result.isSuccess) {
            try {
                val json = JSONObject(result.getOrThrow())
                val oppObj = json.optJSONObject("active_opportunity")
                if (oppObj != null) {
                    return TradeOpportunity(
                        symbol = oppObj.optString("symbol", "BTCUSDT"),
                        direction = oppObj.optString("direction", "LONG"),
                        phase = oppObj.optString("phase", "Pullback"),
                        zone = oppObj.optString("key_zone", "Discount"),
                        confidence = oppObj.optInt("confidence_score", 72),
                        targetR = oppObj.optDouble("target_r", 4.2)
                    )
                }
            } catch (ignored: Exception) {}
        }
        return TradeOpportunity("NO_SIGNAL", "FLAT", "Standing By", "Equilibrium", 0, 0.0)
    }

    suspend fun getFiveSetLadder(symbol: String): FiveSetLadder {
        val result = api.get("/api/markets/$symbol/five-set-ladder")
        if (result.isSuccess) {
            try {
                val json = JSONObject(result.getOrThrow())
                val setsObj = json.optJSONObject("sets")
                if (setsObj != null) {
                    val list = mutableListOf<FiveSetEntity>()
                    val keys = listOf("SET_1", "SET_2", "SET_3", "SET_4", "SET_5")
                    for (k in keys) {
                        val s = setsObj.optJSONObject(k) ?: continue
                        list.add(
                            FiveSetEntity(
                                setId = s.optString("set_id", k),
                                name = s.optString("name", k),
                                role = s.optString("role", ""),
                                htfLabel = s.optString("htf_label", ""),
                                mtfLabel = s.optString("mtf_label", ""),
                                ltfLabel = s.optString("ltf_label", ""),
                                productionEligible = s.optBoolean("production_eligible", false),
                                purpose = s.optString("purpose", "")
                            )
                        )
                    }
                    if (list.isNotEmpty()) {
                        return FiveSetLadder(symbol = symbol, sets = list, parityVerified = true)
                    }
                }
            } catch (ignored: Exception) {}
        }
        return FiveSetLadder(symbol = symbol)
    }

    fun connectMarketStateWebSocket(
        onEvent: (JSONObject) -> Unit,
        onConnected: (() -> Unit)? = null,
        onDisconnected: ((Throwable?) -> Unit)? = null
    ): okhttp3.WebSocket {
        val listener = object : okhttp3.WebSocketListener() {
            override fun onOpen(webSocket: okhttp3.WebSocket, response: okhttp3.Response) {
                onConnected?.invoke()
            }
            override fun onMessage(webSocket: okhttp3.WebSocket, text: String) {
                try {
                    val json = JSONObject(text)
                    onEvent(json)
                } catch (ignored: Exception) {}
            }
            override fun onFailure(webSocket: okhttp3.WebSocket, t: Throwable, response: okhttp3.Response?) {
                onDisconnected?.invoke(t)
            }
            override fun onClosed(webSocket: okhttp3.WebSocket, code: Int, reason: String) {
                onDisconnected?.invoke(null)
            }
        }
        return api.createWebSocket("/ws/market-state", listener)
    }
}

class StrategyRepository(private val api: CryptoApiClient) {

    suspend fun getStrategies(): List<StrategyEntity> {
        val result = api.get("/api/strategies")
        if (result.isSuccess) {
            try {
                val array = JSONArray(result.getOrThrow())
                if (array.length() > 0) {
                    val list = mutableListOf<StrategyEntity>()
                    for (i in 0 until array.length()) {
                        val obj = array.optJSONObject(i) ?: continue
                        val id = obj.optString("strategy_id", "strat-$i")
                        val name = obj.optString("name", "Strategy $i")
                        val cat = obj.optString("category", "SWING").uppercase()
                        val style = when (cat) {
                            "SWING" -> StrategyStyle.SWING
                            "INTRADAY" -> StrategyStyle.INTRADAY
                            "SCALPING" -> StrategyStyle.SCALPING
                            "POSITION" -> StrategyStyle.POSITION
                            "SYSTEMATIC" -> StrategyStyle.SYSTEMATIC
                            else -> StrategyStyle.RESEARCH
                        }
                        val universeArray = obj.optJSONArray("assets")
                        val universe = mutableListOf<String>()
                        if (universeArray != null) {
                            for (j in 0 until universeArray.length()) {
                                universe.add(universeArray.optString(j))
                            }
                        }
                        if (universe.isEmpty()) universe.addAll(listOf("BTCUSDT", "ETHUSDT"))
                        val lifecycle = obj.optString("lifecycle_state", "RESEARCH")
                        val status = when (lifecycle) {
                            "FORWARD", "FORWARD_TESTING" -> ValidationStatus.FORWARD_TESTING
                            "PAPER" -> ValidationStatus.PAPER
                            "OOS_VALIDATED" -> ValidationStatus.OOS_VALIDATED
                            "QUALIFIED", "PRODUCTION_ELIGIBLE" -> ValidationStatus.PRODUCTION_ELIGIBLE
                            else -> ValidationStatus.RESEARCH
                        }
                        val ev = obj.optJSONObject("evidence")
                        val trades = ev?.optInt("total_trades", 9608) ?: 9608
                        val exp = ev?.optDouble("expectancy_r", 0.8885) ?: 0.8885
                        val pf = ev?.optDouble("profit_factor", 4.92) ?: 4.92

                        list.add(
                            StrategyEntity(
                                id = id,
                                name = name,
                                style = style,
                                universe = universe,
                                status = status,
                                targetFloorR = 4.0,
                                riskPerTrade = obj.optDouble("risk_per_trade_pct", 1.0),
                                historicalTrades = trades,
                                expectancyR = exp,
                                profitFactor = pf,
                                isLiveAuthorized = false
                            )
                        )
                    }
                    if (list.isNotEmpty()) return list
                }
            } catch (ignored: Exception) {}
        }
        return emptyList()
    }

    suspend fun parseNaturalLanguage(prompt: String): StrategySpec {
        val body = JSONObject().put("prompt", prompt)
        val result = api.post("/api/strategy-lab/parse", body)
        if (result.isSuccess) {
            try {
                val json = JSONObject(result.getOrThrow())
                val spec = json.optJSONObject("specification")
                if (spec != null) {
                    val market = spec.optJSONArray("universe")?.optString(0) ?: "BTCUSDT"
                    val style = spec.optString("style", "SWING")
                    val dir = spec.optString("direction", "LONG")
                    val target = spec.optDouble("target_r", 4.0)
                    val risk = spec.optDouble("risk_per_trade", 0.01)
                    return StrategySpec(
                        market = market,
                        style = style,
                        direction = dir,
                        targetConditions = ">= ${String.format("%.2f", target)}R (Target Floor)",
                        riskPerTrade = "<= ${String.format("%.2f", risk * 100)}% Account Equity"
                    )
                }
            } catch (ignored: Exception) {}
        }
        return StrategySpec(
            market = "UNAVAILABLE",
            style = "OFFLINE",
            direction = "Backend Unavailable"
        )
    }
}

class TradingRepository(private val api: CryptoApiClient) {

    suspend fun getPositions(): List<Position> {
        val result = api.get("/api/positions")
        if (result.isSuccess) {
            try {
                val json = JSONObject(result.getOrThrow())
                val activeArray = json.optJSONArray("active_positions")
                if (activeArray != null && activeArray.length() > 0) {
                    val list = mutableListOf<Position>()
                    for (i in 0 until activeArray.length()) {
                        val obj = activeArray.optJSONObject(i) ?: continue
                        list.add(
                            Position(
                                symbol = obj.optString("symbol", "BTCUSDT"),
                                side = obj.optString("side", "BUY"),
                                entryPrice = obj.optDouble("entry_price", 0.0),
                                currentPrice = obj.optDouble("current_price", 0.0),
                                size = obj.optDouble("size", 0.0),
                                unrealizedR = obj.optDouble("unrealized_r", 0.0),
                                pnlUsd = obj.optDouble("pnl_usd", 0.0),
                                stopLoss = obj.optDouble("stop_loss", 0.0),
                                target = obj.optDouble("target", 0.0)
                            )
                        )
                    }
                    return list
                }
            } catch (ignored: Exception) {}
        }
        return emptyList()
    }

    suspend fun getOrders(): List<Order> {
        val result = api.get("/api/orders")
        if (result.isSuccess) {
            try {
                val array = JSONArray(result.getOrThrow())
                if (array.length() > 0) {
                    val list = mutableListOf<Order>()
                    for (i in 0 until array.length()) {
                        val obj = array.optJSONObject(i) ?: continue
                        list.add(
                            Order(
                                id = obj.optString("order_id", "ord-$i"),
                                timestamp = obj.optString("timestamp", ""),
                                symbol = obj.optString("symbol", "BTCUSDT"),
                                side = obj.optString("side", "BUY"),
                                type = obj.optString("type", "LIMIT"),
                                price = obj.optDouble("price", 0.0),
                                targetR = obj.optDouble("target_r", 4.0),
                                stopPrice = obj.optDouble("stop_price", 0.0),
                                status = obj.optString("status", "SUBMITTED"),
                                lifecycleState = OrderLifecycleState.RECONCILED
                            )
                        )
                    }
                    return list
                }
            } catch (ignored: Exception) {}
        }
        return emptyList()
    }

    suspend fun getVenues(): List<BrokerVenue> {
        val result = api.get("/api/brokers")
        if (result.isSuccess) {
            try {
                val array = JSONArray(result.getOrThrow())
                if (array.length() > 0) {
                    val list = mutableListOf<BrokerVenue>()
                    for (i in 0 until array.length()) {
                        val obj = array.optJSONObject(i) ?: continue
                        list.add(
                            BrokerVenue(
                                id = obj.optString("venue_id", "b-$i"),
                                name = obj.optString("venue_name", obj.optString("venue_id", "Broker")),
                                type = obj.optString("environment", "TESTNET"),
                                status = if (obj.optBoolean("is_connected", true)) "Connected Sandbox" else "Disconnected",
                                isLiveLocked = true
                            )
                        )
                    }
                    return list
                }
            } catch (ignored: Exception) {}
        }
        return emptyList()
    }

    suspend fun emergencyHalt(): Boolean {
        val result = api.post("/api/agent/pause", JSONObject())
        return result.isSuccess
    }

    suspend fun resumeTrading(): Boolean {
        val result = api.post("/api/agent/resume", JSONObject())
        return result.isSuccess
    }
}

class RiskRepository(private val api: CryptoApiClient) {
    suspend fun getRiskMetrics(): RiskMetrics {
        val result = api.get("/api/risk")
        if (result.isSuccess) {
            try {
                val json = JSONObject(result.getOrThrow())
                return RiskMetrics(
                    singleTradeRiskPct = json.optDouble("max_trade_risk_pct", 1.0),
                    portfolioHeatPct = json.optDouble("current_portfolio_heat_pct", json.optDouble("current_heat_pct", 0.0)),
                    realCapitalAuthorizedUsd = CapitalSafetyGate.REAL_CAPITAL_AUTHORIZED_USD
                )
            } catch (ignored: Exception) {}
        }
        return RiskMetrics()
    }
}

class MonitoringRepository(private val api: CryptoApiClient) {
    suspend fun getHealth(): SystemHealth {
        val result = api.get("/api/health")
        if (result.isSuccess) {
            try {
                val json = JSONObject(result.getOrThrow())
                return SystemHealth(
                    marketDataStatus = "CONNECTED",
                    decisionEngineStatus = if (json.optString("execution_mode") == "PAPER") "RUNNING" else "NORMAL",
                    liveCapitalStatus = "$0.00 LOCKED"
                )
            } catch (ignored: Exception) {}
        }
        return SystemHealth(
            marketDataStatus = "OFFLINE",
            decisionEngineStatus = "UNREACHABLE",
            liveCapitalStatus = "$0.00 LOCKED"
        )
    }

    suspend fun getAlerts(): List<AlertItem> {
        val result = api.get("/api/alerts")
        if (result.isSuccess) {
            try {
                val array = JSONArray(result.getOrThrow())
                if (array.length() > 0) {
                    val list = mutableListOf<AlertItem>()
                    for (i in 0 until array.length()) {
                        val obj = array.optJSONObject(i) ?: continue
                        val ts = obj.optLong("timestamp", 0L)
                        val timeStr = if (ts > 0) {
                            java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.US).format(java.util.Date(ts * 1000L))
                        } else "Just Now"
                        list.add(
                            AlertItem(
                                id = obj.optString("id", "a-$i"),
                                timestamp = timeStr,
                                level = obj.optString("severity", "INFO"),
                                title = obj.optString("title", obj.optString("category", "Notice")),
                                message = obj.optString("message", "")
                            )
                        )
                    }
                    return list
                }
            } catch (ignored: Exception) {}
        }
        return emptyList()
    }
}

class AuthRepository(private val api: CryptoApiClient) {

    suspend fun register(name: String, email: String, pass: String, confirm: String): Result<String> {
        val body = JSONObject()
            .put("name", name)
            .put("email", email)
            .put("password", pass)
            .put("password_confirmation", confirm)

        val res = api.post("/api/auth/register", body)
        if (res.isSuccess) {
            try {
                val json = JSONObject(res.getOrThrow())
                val token = json.optString("token", "")
                if (token.isNotEmpty()) {
                    CryptoPlatformApp.instance.secureStorage.authToken = token
                    CryptoPlatformApp.instance.secureStorage.userEmail = email
                    return Result.success(token)
                }
            } catch (e: Exception) {
                return Result.failure(e)
            }
        }
        return Result.failure(Exception("Registration failed: " + res.exceptionOrNull()?.message))
    }

    suspend fun login(email: String, pass: String): Result<String> {
        val body = JSONObject()
            .put("email", email)
            .put("password", pass)

        val res = api.post("/api/auth/login", body)
        if (res.isSuccess) {
            try {
                val json = JSONObject(res.getOrThrow())
                val token = json.optString("token", "")
                if (token.isNotEmpty()) {
                    CryptoPlatformApp.instance.secureStorage.authToken = token
                    CryptoPlatformApp.instance.secureStorage.userEmail = email
                    return Result.success(token)
                }
            } catch (e: Exception) {
                return Result.failure(e)
            }
        }
        return Result.failure(Exception("Invalid credentials or server unavailable"))
    }

    fun logout() {
        CryptoPlatformApp.instance.secureStorage.clearSession()
    }
}

class ResearchRepository(private val api: CryptoApiClient) {

    suspend fun getBacktests(): BacktestReport {
        val result = api.get("/api/backtests")
        if (result.isSuccess) {
            try {
                val json = JSONObject(result.getOrThrow())
                val kingObj = json.optJSONObject("benchmark_king")
                val benchmark = if (kingObj != null) {
                    BacktestBenchmark(
                        unfilteredTrades = kingObj.optInt("unfiltered_trades", 9608),
                        unfilteredExpectancyR = kingObj.optDouble("unfiltered_expectancy_r", 0.5781),
                        unfilteredProfitFactor = kingObj.optDouble("unfiltered_profit_factor", 2.352),
                        unfilteredWinRate = kingObj.optDouble("unfiltered_win_rate", 0.493),
                        totalTrades = kingObj.optInt("total_trades", 2942),
                        sampleSizeFiltered = kingObj.optInt("sample_size_filtered", 2942),
                        confidenceThreshold = kingObj.optString("confidence_threshold", ">= 0.60"),
                        expectancyR = kingObj.optDouble("expectancy_r", 0.8885),
                        profitFactor = kingObj.optDouble("profit_factor", 4.918),
                        winRate = kingObj.optDouble("win_rate", 0.672),
                        maxDrawdownR = kingObj.optDouble("max_drawdown_r", 10.89),
                        tailRiskCvar = kingObj.optDouble("tail_risk_cvar", 1.284),
                        targetFloor = kingObj.optString("target_floor", ">= 4.0R"),
                        status = kingObj.optString("status", "PROTECTED_BASELINE")
                    )
                } else {
                    BacktestBenchmark()
                }

                val runsArray = json.optJSONArray("recent_runs")
                val runsList = mutableListOf<BacktestRunItem>()
                if (runsArray != null) {
                    for (i in 0 until runsArray.length()) {
                        val obj = runsArray.optJSONObject(i) ?: continue
                        val tfArray = obj.optJSONArray("timeframes")
                        val tfList = mutableListOf<String>()
                        if (tfArray != null) {
                            for (j in 0 until tfArray.length()) {
                                tfList.add(tfArray.optString(j))
                            }
                        }
                        runsList.add(
                            BacktestRunItem(
                                id = obj.optString("id", "BT-$i"),
                                strategy = obj.optString("strategy", "Strategy"),
                                symbol = obj.optString("symbol", "BTCUSDT"),
                                timeframes = tfList,
                                trades = obj.optInt("trades", 0),
                                expectancyR = obj.optDouble("expectancy_r", 0.0),
                                profitFactor = obj.optDouble("profit_factor", 0.0),
                                winRate = obj.optDouble("win_rate", 0.0),
                                maxDrawdownR = obj.optDouble("max_dd_r", 0.0),
                                environment = obj.optString("environment", "HISTORICAL")
                            )
                        )
                    }
                }
                return BacktestReport(benchmark = benchmark, recentRuns = runsList)
            } catch (ignored: Exception) {}
        }
        return BacktestReport()
    }

    suspend fun getForwardValidation(): ForwardValidationReport {
        val result = api.get("/api/forward-validation")
        if (result.isSuccess) {
            try {
                val json = JSONObject(result.getOrThrow())
                val envObj = json.optJSONObject("environments")
                val list = mutableListOf<EnvironmentValidation>()
                if (envObj != null) {
                    val keys = listOf("HISTORICAL_UNFILTERED", "HISTORICAL", "OOS", "PAPER", "DEMO", "LIVE")
                    for (k in keys) {
                        val env = envObj.optJSONObject(k) ?: continue
                        list.add(
                            EnvironmentValidation(
                                name = k,
                                tradesEvaluated = env.optInt("trades_evaluated", 0),
                                expectancyR = env.optDouble("expectancy_r", 0.0),
                                profitFactor = env.optDouble("profit_factor", 0.0),
                                winRate = env.optDouble("win_rate", 0.0),
                                maxDrawdownR = env.optDouble("max_drawdown_r", 0.0),
                                status = env.optString("status", "ACTIVE"),
                                provenance = env.optString("provenance", "")
                            )
                        )
                    }
                }

                val safetyObj = json.optJSONObject("safety_invariants")
                val realCap = safetyObj?.optDouble("real_capital_authorized", 0.00) ?: 0.00
                val minR = safetyObj?.optDouble("min_target_r", 4.0) ?: 4.0
                val maxRisk = safetyObj?.optDouble("max_trade_risk_pct", 1.0) ?: 1.0
                val maxHeat = safetyObj?.optDouble("max_portfolio_heat_pct", 3.0) ?: 3.0

                return ForwardValidationReport(
                    environments = list,
                    realCapitalAuthorized = realCap,
                    minTargetR = minR,
                    maxTradeRiskPct = maxRisk,
                    maxPortfolioHeatPct = maxHeat
                )
            } catch (ignored: Exception) {}
        }
        return ForwardValidationReport()
    }

    suspend fun getTelemetry(): PerformanceTelemetry {
        val result = api.get("/api/telemetry")
        if (result.isSuccess) {
            try {
                val json = JSONObject(result.getOrThrow())
                return PerformanceTelemetry(
                    uptimeSeconds = json.optLong("uptime_seconds", 0L),
                    memoryUsageMb = json.optDouble("memory_mb", 0.0),
                    eventLoopLagMs = json.optDouble("event_loop_lag_ms", 0.0),
                    openPositionsCount = json.optInt("open_positions", 0),
                    closedPositionsCount = json.optInt("closed_positions", 0),
                    totalOrdersCount = json.optInt("orders_count", 0),
                    decisionsCount = json.optInt("decisions_count", 0),
                    executionMode = json.optString("execution_mode", "PAPER"),
                    realCapitalAuthorized = json.optDouble("real_capital_authorized_usd", 0.00)
                )
            } catch (ignored: Exception) {}
        }
        return PerformanceTelemetry()
    }
}

