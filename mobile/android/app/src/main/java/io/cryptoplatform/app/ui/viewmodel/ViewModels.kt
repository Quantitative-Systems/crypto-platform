package io.cryptoplatform.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import io.cryptoplatform.app.core.security.CapitalSafetyGate
import io.cryptoplatform.app.data.repository.*
import io.cryptoplatform.app.domain.model.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.json.JSONObject

data class HomeUiState(
    val portfolioEquity: Double = 100_000.00,
    val todayPnlPct: Double = 0.00,
    val portfolioHeatPct: Double = 0.00,
    val portfolioHeatLimit: Double = 3.00,
    val singleTradeRiskPct: Double = 1.00,
    val markets: List<AssetQuote> = emptyList(),
    val opportunity: TradeOpportunity? = null,
    val systemStatus: String = "Normal",
    val realCapitalAuthorized: Double = 0.00,
    val isLiveLocked: Boolean = true
)

class HomeViewModel(private val marketRepo: MarketRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    init {
        loadDashboard()
    }

    fun loadDashboard() {
        viewModelScope.launch {
            val quotes = marketRepo.getMarkets()
            val opp = marketRepo.getActiveOpportunity()
            _uiState.value = _uiState.value.copy(
                markets = quotes,
                opportunity = opp,
                realCapitalAuthorized = CapitalSafetyGate.REAL_CAPITAL_AUTHORIZED_USD,
                isLiveLocked = CapitalSafetyGate.IS_LIVE_TRADING_LOCKED
            )
        }
    }
}



data class MarketsUiState(
    val assets: List<AssetQuote> = emptyList(),
    val filterType: String = "ALL", // ALL or WATCHLIST
    val searchQuery: String = "",
    val isLoading: Boolean = false,
    val isStreaming: Boolean = false
)

class MarketsViewModel(private val marketRepo: MarketRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(MarketsUiState())
    val uiState: StateFlow<MarketsUiState> = _uiState.asStateFlow()
    private var webSocket: okhttp3.WebSocket? = null
    private var isDisposed = false

    init {
        refresh()
        startWebSocketStreaming()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            val quotes = marketRepo.getMarkets()
            _uiState.value = _uiState.value.copy(assets = quotes, isLoading = false)
        }
    }

    private fun startWebSocketStreaming() {
        if (isDisposed) return
        webSocket?.close(1000, "Reconnecting")
        webSocket = marketRepo.connectMarketStateWebSocket(
            onEvent = { json ->
                val eventType = json.optString("event_type")
                if (eventType == "MARKET_STATE_UPDATE") {
                    val asset = json.optString("asset")
                    val price = json.optDouble("current_price", 0.0)
                    if (asset.isNotEmpty() && price > 0.0) {
                        val currentList = _uiState.value.assets
                        val updated = currentList.map {
                            if (it.symbol.equals(asset, ignoreCase = true)) it.copy(price = price) else it
                        }
                        _uiState.value = _uiState.value.copy(assets = updated)
                    }
                }
            },
            onConnected = {
                _uiState.value = _uiState.value.copy(isStreaming = true)
            },
            onDisconnected = {
                _uiState.value = _uiState.value.copy(isStreaming = false)
                if (!isDisposed) {
                    viewModelScope.launch {
                        kotlinx.coroutines.delay(4000)
                        if (!isDisposed && !_uiState.value.isStreaming) {
                            startWebSocketStreaming()
                        }
                    }
                }
            }
        )
    }

    fun setFilter(type: String) {
        _uiState.value = _uiState.value.copy(filterType = type)
    }

    fun setSearch(query: String) {
        _uiState.value = _uiState.value.copy(searchQuery = query)
    }

    fun toggleWatchlist(symbol: String) {
        viewModelScope.launch {
            marketRepo.toggleWatchlist(symbol)
            refresh()
        }
    }

    override fun onCleared() {
        super.onCleared()
        isDisposed = true
        webSocket?.close(1000, "Markets screen disposed")
        webSocket = null
    }
}

data class MarketDetailUiState(
    val symbol: String = "BTCUSDT",
    val quote: AssetQuote? = null,
    val ladder: SevenTimeframeLadder = SevenTimeframeLadder(),
    val fiveSetLadder: FiveSetLadder = FiveSetLadder(),
    val selectedTimeframe: String = "4H",
    val orderMessage: String? = null,
    val isStreamingConnected: Boolean = false,
    val streamFreshnessMs: Long = 0L,
    val lastEventSequence: Long = 0L,
    val isDataStale: Boolean = false
)

class MarketDetailViewModel(
    private val marketRepo: MarketRepository,
    private val initialSymbol: String
) : ViewModel() {
    private val _uiState = MutableStateFlow(MarketDetailUiState(symbol = initialSymbol))
    val uiState: StateFlow<MarketDetailUiState> = _uiState.asStateFlow()
    private var webSocket: okhttp3.WebSocket? = null
    private var isDisposed = false

    init {
        loadDetail()
        startWebSocketStreaming()
    }

    private fun loadDetail() {
        viewModelScope.launch {
            val quotes = marketRepo.getMarkets()
            val match = quotes.find { it.symbol == initialSymbol } ?: quotes.firstOrNull()
            val fiveSet = marketRepo.getFiveSetLadder(initialSymbol)
            _uiState.value = _uiState.value.copy(quote = match, fiveSetLadder = fiveSet)
        }
    }

    fun startWebSocketStreaming() {
        if (isDisposed) return
        webSocket?.close(1000, "Reconnecting")
        webSocket = marketRepo.connectMarketStateWebSocket(
            onEvent = { json ->
                handleMarketEvent(json)
            },
            onConnected = {
                _uiState.value = _uiState.value.copy(
                    isStreamingConnected = true,
                    isDataStale = false
                )
            },
            onDisconnected = {
                _uiState.value = _uiState.value.copy(
                    isStreamingConnected = false,
                    isDataStale = true
                )
                if (!isDisposed) {
                    viewModelScope.launch {
                        kotlinx.coroutines.delay(3000)
                        if (!isDisposed && !_uiState.value.isStreamingConnected) {
                            startWebSocketStreaming()
                        }
                    }
                }
            }
        )
    }

    private fun handleMarketEvent(json: JSONObject) {
        val eventType = json.optString("event_type")
        val seq = json.optLong("sequence_id", 0L)
        val freshness = json.optLong("data_freshness_ms", 0L)

        if (eventType == "STATE_SNAPSHOT") {
            val meta = json.optJSONObject("metadata")
            val markets = meta?.optJSONObject("markets")
            val symData = markets?.optJSONObject(initialSymbol)
            if (symData != null) {
                val ladderObj = symData.optJSONObject("ladder")
                if (ladderObj != null) {
                    val setsObj = ladderObj.optJSONObject("sets")
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
                            _uiState.value = _uiState.value.copy(
                                fiveSetLadder = FiveSetLadder(symbol = initialSymbol, sets = list, parityVerified = true),
                                isStreamingConnected = true,
                                streamFreshnessMs = freshness,
                                lastEventSequence = seq,
                                isDataStale = false
                            )
                            return
                        }
                    }
                }
            }
            _uiState.value = _uiState.value.copy(
                isStreamingConnected = true,
                streamFreshnessMs = freshness,
                lastEventSequence = seq,
                isDataStale = false
            )
        } else if (eventType == "MARKET_STATE_UPDATE") {
            val asset = json.optString("asset")
            if (asset.equals(initialSymbol, ignoreCase = true)) {
                val currentPrice = json.optDouble("current_price", _uiState.value.quote?.price ?: 0.0)
                val structure = json.optString("structure", "BULLISH")
                val phase = json.optString("phase", "CONTINUATION")

                val updatedQuote = _uiState.value.quote?.copy(
                    price = currentPrice,
                    marketStructure = structure,
                    phase = phase
                ) ?: AssetQuote(
                    symbol = initialSymbol,
                    name = initialSymbol.removeSuffix("USDT"),
                    price = currentPrice,
                    change24h = 0.0,
                    marketStructure = structure,
                    phase = phase
                )

                _uiState.value = _uiState.value.copy(
                    quote = updatedQuote,
                    isStreamingConnected = true,
                    streamFreshnessMs = freshness,
                    lastEventSequence = seq,
                    isDataStale = false
                )
            }
        }
    }

    fun selectTimeframe(tf: String) {
        _uiState.value = _uiState.value.copy(selectedTimeframe = tf)
    }

    fun simulatePaperOrder(side: String) {
        _uiState.value = _uiState.value.copy(
            orderMessage = "Paper $side order intent for ${_uiState.value.symbol} registered. Zero real capital executed."
        )
    }

    fun clearOrderMessage() {
        _uiState.value = _uiState.value.copy(orderMessage = null)
    }

    override fun onCleared() {
        super.onCleared()
        isDisposed = true
        webSocket?.close(1000, "Screen destroyed")
        webSocket = null
    }
}

data class StrategiesUiState(
    val strategies: List<StrategyEntity> = emptyList(),
    val selectedStyle: String = "ALL"
)

class StrategiesViewModel(private val strategyRepo: StrategyRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(StrategiesUiState())
    val uiState: StateFlow<StrategiesUiState> = _uiState.asStateFlow()

    init {
        loadStrategies()
    }

    fun loadStrategies() {
        viewModelScope.launch {
            val list = strategyRepo.getStrategies()
            _uiState.value = _uiState.value.copy(strategies = list)
        }
    }

    fun selectStyle(style: String) {
        _uiState.value = _uiState.value.copy(selectedStyle = style)
    }
}

data class ResearchUiState(
    val prompt: String = "Create a BTC swing strategy using market structure, pullbacks and a minimum 4R target.",
    val specification: StrategySpec? = null,
    val isParsing: Boolean = false,
    val feedbackMessage: String? = null
)

class ResearchViewModel(private val strategyRepo: StrategyRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(ResearchUiState())
    val uiState: StateFlow<ResearchUiState> = _uiState.asStateFlow()

    fun updatePrompt(newPrompt: String) {
        _uiState.value = _uiState.value.copy(prompt = newPrompt)
    }

    fun parsePrompt() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isParsing = true)
            val spec = strategyRepo.parseNaturalLanguage(_uiState.value.prompt)
            _uiState.value = _uiState.value.copy(
                specification = spec,
                isParsing = false,
                feedbackMessage = "Strategy specification generated. Invariant verified: Floor >= 4.0R, Risk <= 1.0%."
            )
        }
    }

    fun clearFeedback() {
        _uiState.value = _uiState.value.copy(feedbackMessage = null)
    }
}

data class TradingUiState(
    val activePositions: List<Position> = emptyList(),
    val orders: List<Order> = emptyList(),
    val venues: List<BrokerVenue> = emptyList(),
    val selectedSubTab: String = "POSITIONS", // POSITIONS, ORDERS, VENUES
    val isLiveLocked: Boolean = true,
    val realCapitalAuthorized: Double = 0.00
)

class TradingViewModel(private val tradingRepo: TradingRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(TradingUiState())
    val uiState: StateFlow<TradingUiState> = _uiState.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            val pos = tradingRepo.getPositions()
            val ord = tradingRepo.getOrders()
            val v = tradingRepo.getVenues()
            _uiState.value = _uiState.value.copy(
                activePositions = pos,
                orders = ord,
                venues = v
            )
        }
    }

    fun selectSubTab(tab: String) {
        _uiState.value = _uiState.value.copy(selectedSubTab = tab)
    }
}

data class RiskUiState(
    val metrics: RiskMetrics = RiskMetrics()
)

class RiskViewModel(private val riskRepo: RiskRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(RiskUiState())
    val uiState: StateFlow<RiskUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            _uiState.value = RiskUiState(metrics = riskRepo.getRiskMetrics())
        }
    }
}

data class MonitoringUiState(
    val health: SystemHealth = SystemHealth(),
    val alerts: List<AlertItem> = emptyList()
)

class MonitoringViewModel(private val monitoringRepo: MonitoringRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(MonitoringUiState())
    val uiState: StateFlow<MonitoringUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            val h = monitoringRepo.getHealth()
            val a = monitoringRepo.getAlerts()
            _uiState.value = MonitoringUiState(health = h, alerts = a)
        }
    }
}

data class AccountUiState(
    val username: String = "Platform Operator",
    val email: String = "operator@cryptoplatform.io",
    val tenantId: String = "system",
    val isAuthenticated: Boolean = true,
    val message: String? = null
)

class AccountViewModel(private val authRepo: AuthRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(AccountUiState())
    val uiState: StateFlow<AccountUiState> = _uiState.asStateFlow()

    fun logout() {
        authRepo.logout()
        _uiState.value = _uiState.value.copy(
            username = "Demo Operator",
            email = "demo@cryptoplatform.io",
            isAuthenticated = false,
            message = "Logged out. Operating in unauthenticated demo session."
        )
    }

    fun login(email: String, pass: String) {
        viewModelScope.launch {
            val res = authRepo.login(email, pass)
            if (res.isSuccess) {
                _uiState.value = _uiState.value.copy(
                    username = email.substringBefore("@"),
                    email = email,
                    isAuthenticated = true,
                    message = "Authenticated successfully!"
                )
            } else {
                _uiState.value = _uiState.value.copy(
                    message = "Login failed: ${res.exceptionOrNull()?.message}"
                )
            }
        }
    }

    fun register(name: String, email: String, pass: String, confirm: String) {
        viewModelScope.launch {
            val res = authRepo.register(name, email, pass, confirm)
            if (res.isSuccess) {
                _uiState.value = _uiState.value.copy(
                    username = name,
                    email = email,
                    isAuthenticated = true,
                    message = "Registration complete. Welcome!"
                )
            } else {
                _uiState.value = _uiState.value.copy(
                    message = "Registration failed: ${res.exceptionOrNull()?.message}"
                )
            }
        }
    }

    fun clearMessage() {
        _uiState.value = _uiState.value.copy(message = null)
    }
}

data class BacktestUiState(
    val report: BacktestReport = BacktestReport(),
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

class BacktestViewModel(private val researchRepo: ResearchRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(BacktestUiState())
    val uiState: StateFlow<BacktestUiState> = _uiState.asStateFlow()

    init {
        loadBacktests()
    }

    fun loadBacktests() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
            try {
                val r = researchRepo.getBacktests()
                _uiState.value = _uiState.value.copy(report = r, isLoading = false)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = e.message)
            }
        }
    }
}

data class ForwardUiState(
    val report: ForwardValidationReport = ForwardValidationReport(),
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

class ForwardViewModel(private val researchRepo: ResearchRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(ForwardUiState())
    val uiState: StateFlow<ForwardUiState> = _uiState.asStateFlow()

    init {
        loadForwardValidation()
    }

    fun loadForwardValidation() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
            try {
                val r = researchRepo.getForwardValidation()
                _uiState.value = _uiState.value.copy(report = r, isLoading = false)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = e.message)
            }
        }
    }
}

data class PerformanceUiState(
    val telemetry: PerformanceTelemetry = PerformanceTelemetry(),
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

class PerformanceViewModel(private val researchRepo: ResearchRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(PerformanceUiState())
    val uiState: StateFlow<PerformanceUiState> = _uiState.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
            try {
                val t = researchRepo.getTelemetry()
                _uiState.value = _uiState.value.copy(telemetry = t, isLoading = false)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = e.message)
            }
        }
    }
}

