# NBA Underdog Bet - Roadmap

## Versions

| Version | Focus | Status |
|---------|-------|--------|
| v0.1.0 | MVP - Fetch, Analyse, Export | Done |
| v0.1.5 | Kelly Criterion Sizing | Done |
| v0.2.0 | Result Tracking | Next |
| v0.3.0 | Agent Memory | Planned |
| v0.4.0 | Notifications | Planned |
| v0.5.0 | Advanced Stats + Simulator | Planned |
| v0.6.0 | AI Master Bettor (Full) | Planned |

---

## v0.1.0 - MVP (Done)

- Fetch matchs NBA via BallDontLie API
- Fetch cotes live via The Odds API
- Filtre underdogs (spread +3.5-7.5, ML +150-300)
- Analyse AI via Pydantic AI + OpenRouter
- Export CSV des picks
- Team matching robuste
- Detection B2B et rest days
- Player injuries

---

## v0.1.5 - Kelly Criterion Sizing (Done)

**Objectif**: Sizing intelligent des mises basé sur Kelly Criterion

**Features:**
- Calcul Kelly Criterion (`f* = (bp - q) / b`)
- Quarter Kelly par défaut (0.25) pour réduire variance
- Cap 5% max bankroll par bet
- Min 0.5% pour éviter micro-bets
- Edge estimation: +8% HIGH, +4% MEDIUM, 0% LOW
- Expected Value (EV) calculation
- Display amélioré: "2.3% ($23)" au lieu de "2 units"

**Config (.env):**
- `BANKROLL=1000.0`
- `KELLY_FRACTION=0.25`
- `MAX_BET_PCT=0.05`
- `MIN_BET_PCT=0.005`

**Livrables:**
- `src/utils/kelly.py`
- BetRecommendation enrichi avec Kelly data
- CSV export avec colonnes Kelly

---

## v0.2.0 - Result Tracking (Next)

**Objectif**: Mesurer la performance des picks

**Features:**
- Schema DB SQLite pour picks et resultats
- Sauvegarde auto des picks HIGH/MEDIUM
- Script fetch resultats post-match
- Metriques: Win rate, ROI, stats par confidence

**Livrables:**
- `data/picks.db`
- `scripts/fetch_results.py`
- `scripts/report.py`

---

## v0.3.0 - Agent Memory

**Objectif**: L'agent se souvient des picks passes

**Features:**
- Historique picks stocke
- Contexte enrichi avec performance passee
- Patterns recognition par equipe

---

## v0.4.0 - Notifications

**Objectif**: Alertes pour picks HIGH confidence

**Options:**
- Discord webhook
- Telegram bot

---

## v0.5.0 - Advanced Stats + Simulator

**Objectif**: Donnees avancees et simulation

**Features:**
- Defensive ratings
- Pace/tempo matchups
- Monte Carlo simulation
- Expected value calculation

---

## v0.6.0 - AI Master Bettor

**Objectif**: Gestion intelligente du bankroll et sizing optimal des mises

**Features:**

### Kelly Criterion Calculator
- Calcul mathematique du % optimal de bankroll
- `f* = (bp - q) / b` ou b=odds, p=win prob, q=1-p
- Protection contre les bets excessifs (cap a 5% bankroll)

### AI Bankroll Manager
- Agent AI dedie a la gestion du bankroll
- Inputs: bankroll actuel, historique performance, volatilite
- Ajuste le sizing selon:
  - Confidence level du pick
  - Win probability estimee (implicite des cotes + edge)
  - Streak actuelle (win/loss)
  - Variance recente

### EV-Based Sizing
- Expected Value = (Win Prob * Potential Win) - (Loss Prob * Stake)
- Scaling automatique selon EV+

### Outputs ameliores
- Recommandation en % de bankroll (pas juste "units")
- Risk score par pick
- Projection P&L journaliere
- Alertes si overexposure

**Livrables:**
- `src/agents/bankroll_agent.py`
- `src/utils/kelly.py`
- Config bankroll dans `.env`
- Dashboard P&L dans output

---

## Considerations techniques

### Timing
- Sweet spot: 2-4h avant tip-off
- Plus tot = plus d'edge, moins precis
- Plus tard = plus precis, lignes ajustees

### Backtesting
- The Odds API = cotes live seulement
- Forward tracking maintenant
- Backtest plus tard avec data accumulee

### Rate Limits
- BallDontLie: 60 req/min
- The Odds API: 500 req/month
- OpenRouter: ~$0.01/call

---

## Dev Workflow

1. Planning (Archon tasks)
2. Dev
3. Test
4. Debug
5. Git tag version
6. Next feature
