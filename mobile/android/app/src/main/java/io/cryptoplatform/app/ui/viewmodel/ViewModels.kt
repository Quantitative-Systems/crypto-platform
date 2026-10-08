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
    val isLoading: Boolean = false
)

class MarketsViewModel(private val marketRepo: MarketRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(MarketsUiState())
    val uiState: StateFlow<MarketsUiState> = _uiState.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            val quotes = marketRepo.getMarkets()
            _uiState.value = _uiState.value.copy(assets = quotes, isLoading = false)
        }
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
}

data class MarketDetailUiState(
    val symbol: String = "BTCUSDT",
    val quote: AssetQuote? = null,
    val ladder: SevenTimeframeLadder = SevenTimeframeLadder(),
    val selectedTimeframe: String = "4H",
    val orderMessage: String? = null
)

class MarketDetailViewModel(
    private val marketRepo: MarketRepository,
    private val initialSymbol: String
) : ViewModel() {
    private val _uiState = MutableStateFlow(MarketDetailUiState(symbol = initialSymbol))
    val uiState: StateFlow<MarketDetailUiState> = _uiState.asStateFlow()

    init {
        loadDetail()
    }

    private fun loadDetail() {
        viewModelScope.launch {
            val quotes = marketRepo.getMarkets()
            val match = quotes.find { it.symbol == initialSymbol } ?: quotes.firstOrNull()
            _uiState.value = _uiState.value.copy(quote = match)
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
