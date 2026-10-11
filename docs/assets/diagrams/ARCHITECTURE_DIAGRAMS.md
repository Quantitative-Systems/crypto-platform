# Crypto Platform — Architecture Diagrams & Data Flows

This document contains the authoritative Mermaid diagrams representing the actual, verified subsystems and workflows of the **Crypto Platform**.

---

## 1. System Architecture

```mermaid
graph TD
    subgraph Ingestion [Market Data Ingestion]
        BinanceFeed["Binance Public WebSocket / REST"] --> MarketSvc["MarketService"]
        LocalCache["Historical Data Cache (Parquet/JSON)"] --> MarketSvc
        MarketSvc --> CandleEng["7-Timeframe Candle Engine<br/>1M → 1W → 1D → 4H → 1H → 15M → 3M"]
    end

    subgraph CoreEngine [Authoritative Core Engine]
        CandleEng --> Supervisor["AutonomousTradingSupervisor"]
        Supervisor --> LadderSets["5 Overlapping Timeframe Observation Sets<br/>Set 1 to Set 5"]
        LadderSets --> DecisionEng["Phase R Decision Engine<br/>Frozen Contract Hash: 8fbc923a..."]
        DecisionEng --> RiskGov["Portfolio Risk Governor<br/>Min Destination Floor &gt;= 4.0R | Max Risk &lt;= 1.0%"]
        RiskGov --> SafetyGate["Fail-Closed Capital Gate<br/>Real Capital: $0.00 | Live Orders: Disabled"]
    end

    subgraph PersistenceLayer [Durable Persistence & Audit]
        Supervisor <--> SQLiteWAL["SQLite WAL Database<br/>crypto_platform.db (Schema v4)"]
        Supervisor <--> DualSnap["Dual JSON Checkpoints<br/>data/checkpoints &amp; research/results"]
        Supervisor --> Ledger["Append-Only Decision Ledger<br/>SHA-256 Event Lineage"]
    end

    subgraph ServerLayer [Institutional Server Layer]
        Supervisor --> WebServer["PhaseRWebServer<br/>aiohttp Asynchronous Server"]
        WebServer --> SecurityMW["Security Middleware<br/>Rate Limiting (240 req/min) &amp; Headers"]
    end

    subgraph ClientLayer [Synchronized Client Workstations]
        SecurityMW --> RestAPI["REST API (21 Endpoints)<br/>/api/health, /api/markets, /api/telemetry"]
        SecurityMW --> WSStream["WebSocket Streaming<br/>/ws/market-state"]
        RestAPI --> WebWorkstation["Institutional Web Workstation<br/>app_terminal.html"]
        WSStream --> WebWorkstation
        RestAPI --> AndroidApp["Native Android Application<br/>Kotlin / Jetpack Compose"]
        WSStream --> AndroidApp
    end
```

---

## 2. Market-Data Lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant Feed as Binance WS / Local Cache
    participant Svc as MarketService
    participant Candle as 7-Timeframe Candle Engine
    participant Sup as AutonomousTradingSupervisor
    participant Model as MarketStateGenerator
    participant Clients as Web & Android Clients

    Feed->>Svc: Raw Tick / 15M Bar Update
    Svc->>Candle: Ingest & Synthesize Multi-Scale Bars
    Note over Candle: Aggregates across 1M, 1W, 1D, 4H, 1H, 15M, 3M
    Candle-->>Sup: On Candle Close Event (Causal, No Future Leakage)
    Sup->>Model: Compute Market State Primitives (Structure, Zones, Phase)
    Model-->>Sup: Authoritative MarketState Object
    Sup->>Sup: Evaluate 5 Overlapping Observation Sets
    Sup->>Clients: Broadcast via WebSocket (/ws/market-state)
    Note over Clients: Both clients update blotters and ladder inspectors in real time
```

---

## 3. Market-State Model Hierarchy

```mermaid
graph TD
    subgraph MarketModel [Canonical Market Model]
        HOW["HOW: Market Structure & Trend<br/>Swing Highs/Lows, CHOCH/MSS, BOS"]
        WHERE["WHERE: Key Zones & Levels<br/>Order Blocks, FVGs, Liquidity Pools, Discount &gt; 50%"]
        WHAT["WHAT: Phase State<br/>Primary: PULLBACK vs CONTINUATION"]
    end

    HOW --> Confluence["Multi-Scale State Confluence"]
    WHERE --> Confluence
    WHAT --> Confluence

    subgraph PhaseStates [Phase Classification & Internal Transitions]
        PULLBACK["PULLBACK (Primary)<br/>Counter-trend retrace into high-timeframe key zones"]
        CONTINUATION["CONTINUATION (Primary)<br/>Trend resumption with structural break validation"]
        CONSOLIDATION["CONSOLIDATION (Internal Transition)<br/>Range-bound equilibrium; reduced trading confidence"]
        UNCERTAIN["UNCERTAIN (Fail-Closed Default)<br/>Ambiguous structure; NO_TRADE policy enforced"]
    end

    WHAT -.-> PULLBACK
    WHAT -.-> CONTINUATION
    WHAT -.-> CONSOLIDATION
    WHAT -.-> UNCERTAIN
```

---

## 4. Seven-Timeframe Continuous Ladder

```mermaid
graph LR
    M1["1M<br/>Macro Context"] --> W1["1W<br/>Macro Trend"]
    W1 --> D1["1D<br/>Structural Bias"]
    D1 --> H4["4H<br/>Intermediate Swing"]
    H4 --> H1["1H<br/>Tactical Setup"]
    H1 --> M15["15M<br/>Execution Trigger"]
    M15 --> M3["3M<br/>Micro Structure"]

    style M1 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style W1 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    style D1 fill:#1e293b,stroke:#0ea5e9,stroke-width:2px,color:#f8fafc
    style H4 fill:#1e293b,stroke:#0284c7,stroke-width:2px,color:#f8fafc
    style H1 fill:#1e293b,stroke:#0369a1,stroke-width:2px,color:#f8fafc
    style M15 fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#f8fafc
    style M3 fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#f8fafc
```

---

## 5. Five Overlapping Timeframe Observation Sets

```mermaid
graph TD
    Ladder["7-Timeframe Ladder: 1M → 1W → 1D → 4H → 1H → 15M → 3M"]
    
    subgraph Sets [Overlapping Observation Windows over ONE Single Ladder]
        SET1["SET 1: 1M → 1W → 1D<br/>Macro Context & Long-Term Trend<br/>Role: Macro Anchor & Destination (Zero Capital)"]
        SET2["SET 2: 1W → 1D → 4H<br/>Structural Foundation<br/>Role: Swing Execution Window (Paper Eligible)"]
        SET3["SET 3: 1D → 4H → 1H<br/>Intermediate Trend & Intraday Bias<br/>Role: Core Execution Window (Paper Eligible)"]
        SET4["SET 4: 4H → 1H → 15M<br/>Operational Swing<br/>Role: Tactical Setup Window (Paper Eligible)"]
        SET5["SET 5: 1H → 15M → 3M<br/>Micro Confirmation<br/>Role: Micro Observation Trigger (Zero Capital)"]
    end

    Ladder --> SET1
    Ladder --> SET2
    Ladder --> SET3
    Ladder --> SET4
    Ladder --> SET5
```

---

## 6. Research & Validation Lifecycle

```mermaid
stateDiagram-v2
    [*] --> HypothesisFormation: Quantitative Hypothesis
    HypothesisFormation --> RuleFormalization: Explicit Entry / Invalidation Rules
    RuleFormalization --> HistoricalReplay: Historical Bar Replay (9,608 Candidates)
    HistoricalReplay --> MetricValidation: Target Geometry (>= 4.0R) & Invariants
    
    state ValidationGates <<choice>>
    MetricValidation --> ValidationGates
    ValidationGates --> Rejected: Failed R Floor / Friction Shortfall
    ValidationGates --> OutOfSampleEvaluation: Passed Strict In-Sample Criteria
    
    OutOfSampleEvaluation --> OOSGates <<choice>>
    OOSGates --> Rejected: Edge Decay / Overfitting Detected
    OOSGates --> PaperShadowValidation: Passed OOS Validation (July 2024+)
    
    PaperShadowValidation --> ProductionEligibilityReview: 24/7 Continuous Paper Tracking
    ProductionEligibilityReview --> [*]: Paper Execution (Real Capital $0.00 LOCKED)

    note right of Rejected
        Rejected experiments preserved in 
        research logs with failure rationale
    end note
```

---

## 7. Trade Lifecycle & Safety Controls

```mermaid
flowchart TD
    Start([New Closed Candle Event]) --> HTFBias{HTF Directional Bias & Destination Verified?}
    HTFBias -- No --> NoTrade[Policy: NO_TRADE]
    HTFBias -- Yes --> MTFSetup{MTF Key Zone & Setup Validated?}
    
    MTFSetup -- No --> NoTrade
    MTFSetup -- Yes --> LTFTrigger{LTF Structure Confirmation & Entry Invalidation?}
    
    LTFTrigger -- No --> NoTrade
    LTFTrigger -- Yes --> GeomCheck{Destination Floor >= 4.0R<br/>& Risk <= 1.0%?}
    
    GeomCheck -- No --> RejectGeom[Reject: Geometry Sub-Floor]
    GeomCheck -- Yes --> HeatCheck{Portfolio Heat <= 3.0%<br/>& Asset Exposure <= 1.0%?}
    
    HeatCheck -- No --> RejectHeat[Reject: Risk Governor Cap]
    HeatCheck -- Yes --> SafetyCheck{Live Capital Authorized == $0.00?}
    
    SafetyCheck -- Live Order Attempt --> Block[FAIL-CLOSED LOCK: Order Blocked]
    SafetyCheck -- Paper Execution --> PaperFill[Simulated Next-Bar Fill Logged]
    
    PaperFill --> LedgerRecord[Append Immutable Decision to SQLite & Checkpoints]
    LedgerRecord --> ActiveBlotter[Monitor Position: Trailing Stop / Destination Exit]
```

---

## 8. Deployment Topology & Environmental Boundaries

```mermaid
graph TD
    subgraph LocalEnv [Local Development & Testing (Fully Operational)]
        DevPython["Python 3.12 Authoritative Backend<br/>python main.py / cli.py"]
        DevWeb["Institutional Web Workstation<br/>http://localhost:8080/dashboard"]
        DevAndroid["Android Native Emulator / Debug APK<br/>Connected via 10.0.2.2:8080"]
        DevDB["Local SQLite WAL DB<br/>data/db/crypto_platform.db"]
    end

    subgraph CIEnv [GitHub Actions Standard CI (100% Green)]
        CIPython["Quantitative Core & Regression Suite<br/>300 Tests | 9,608 Invariant Replay"]
        CIAndroid["Android Build Pipeline (Temurin JDK 17)<br/>assembleDebug | assembleStaging | assembleRelease"]
        CIArtifacts["Artifact Uploads (14-day retention)<br/>Debug APK | Staging APK | Release APK"]
    end

    subgraph StagingConfig [Staging Configuration (Blueprint Ready)]
        RenderSpec["render.yaml Blueprint<br/>Configured for web service & worker"]
        StagingURL["https://crypto-platform-staging.onrender.com<br/>Target mapped in Web & Android code"]
        RenderNote["⚠️ Not Live Provisioned<br/>Requires user GitHub linking & account provision"]
    end

    LocalEnv -.->|Validated via| CIEnv
    CIEnv -.->|Prepares Artifacts for| StagingConfig
```
