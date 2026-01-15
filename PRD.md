PRD — Système de Betting Underdogs NBA
1. Vision
Développer un système automatisé, AI-powered et from scratch pour identifier et analyser les opportunités de value sur les underdogs NBA (équipes non favorites), en se concentrant sur les spreads ATS et moneyline ML. L'outil agira comme un "smart bettor agent" qui fetch data live, applique une stratégie contrarian/data-driven, et output des recommandations de bets avec confidence scores. À long terme, il évoluera en un dashboard pour tracker ROI, en restant éthique (pas de betting auto, juste insights). Vision ultime : Un edge rentable (+5-10 units/100 bets) focalisé sur NBA 2025-2026 trends.
2. Problem
Les bettors NBA manquent d'outils simples pour spotter underdogs value (e.g., road dogs +3.5-7.5 avec fatigue fav). Les APIs comme BallDon'tLie All-Star limitent les advanced stats, rendant le backtesting dur. Les analyses manuelles sont time-consuming, et le marché est efficient – besoin d'AI pour patterns subtils (B2B, injuries, public bias). Sans framework agentic, les systèmes sont messy. Solution actuelle : Scripts ad-hoc, mais pas un agent autonome.
3. Target Users

Bettors NBA amateurs/pros avec accès APIs et tools dev (Cursor, OpenRouter).
Utilisateurs intéressés par underdogs (NBA), avec bankroll modéré.
Niveau tech : Intermédiaire (peut coder/debug avec Claude), focus sur actionable insights sans complexité overkill.

4. Goals (In Scope)

Build un système from scratch utilisant Pydantic AI comme framework agentic pour agents type-safe, outils intégrés, et outputs structurés.
Implémenter une stratégie complète : Filters underdogs sur spreads et ML, checks B2B/injuries, AI analysis via OpenRouter.
Utiliser Archon comme backbone pour knowledge/task management, MCP server pour intégration AI (e.g., avec Cursor/Claude), et deployment Docker.
Créer un "smart bettor agent" avec loop (observe-reason-act) pour reco bets sur spreads et ML.
Supporter MVP : Daily runs pour upcoming games, output tables avec picks.
Intégrer alternatives pour limites All-Star (e.g., web searches pour advanced data).
Équilibre spreads vs ML : Tout implémenter pour que la stratégie couvre les deux de manière équilibrée.

5. Non-Goals (Out of Scope)

Pas de betting automatique (e.g., intégration bookmakers APIs).
Pas de ML training avancé (reste AI prompt-based via OpenRouter et Pydantic AI).
Pas de full web app au MVP (optionnel avec Vite.js later).
Pas de support multi-sports (focus NBA underdogs spreads/ML).
Pas de data storage DB complexe (utilise files/JSON ou Archon pour persistence simple).

6. Constraints (Tech / Cost / Legal / Time)

Tech : Limites All-Star (60 req/min, pas de boxscores/odds – mitigation : proxies via /stats, ou web_search pour supplements). The Odds API free tier (500 req/mo). OpenRouter pay-per-use (~$0.01/call). Pydantic AI pour agents (Python-based). Archon pour MCP/knowledge (Docker setup requis). Intégration Pydantic AI avec Archon : Pas de blocage spécifique identifié, procéder avec setup standard (e.g., Archon pour tasks, Pydantic AI pour agents type-safe).
Cost : < $20/mo initial (All-Star $10 + OpenRouter/The Odds API). Si nécessaire pour advanced (e.g., upgrade GOAT $39.99/mo pour boxscores/odds), justifier car money brings money (ROI potentiel via edges betting).
Legal : Pas d'usage commercial ; respecte TOS APIs (pas de scraping illégal). Betting insights only – rappelle "bet responsibly" (conforme laws où betting légal).
Time : 4-8h pour MVP (avec Claude in Cursor). Iterations : 1-2 jours.

7. Requirements
Functional

Fetch odds live (spreads/ML) et identifier underdogs.
Fetch stats basiques (win rates, injuries, B2B via schedules).
AI analysis via Pydantic AI agents : Outputs structurés (e.g., BaseModel pour reco), tool calls pour APIs.
Intégrer Archon pour knowledge (e.g., crawl docs betting trends), task mgmt (e.g., backtest workflows), et MCP pour AI integration.
Output : Table Pandas/CSV avec picks (game, underdog, spread/ML, AI reco).
Agent loop : Autonomous (fetch-analyze-decide-track bankroll sim) via Pydantic AI.

Non-functional (reliability, cost controls, performance)

Reliability : Handle API errors (try/except), cache data pour éviter rate limits ; use Pydantic validation.
Cost Controls : Limit AI calls (e.g., 1/game), use free tiers max ; upgrade si ROI justifié.
Performance : Run <5min pour daily analysis (10-15 games NBA) ; Archon pour efficient querying.

8. Data / Integrations (if any)

BallDon'tLie All-Star : /teams, /players, /games (B2B), /stats (basics), /player_injuries.
The Odds API : Odds live (spreads, ML, totals).
OpenRouter : Router AI calls (Claude/GPT pour analysis), intégré via Pydantic AI tools.
Pydantic AI : Framework pour agents, data models, tool integration.
Archon : MCP server pour knowledge/task mgmt, RAG pour trends, deployment Docker.
Alternatives si limites : Web_search/browse_page pour advanced stats (e.g., Basketball-Reference trends).

9. MVP Scope (v0)

Agent basique via Pydantic AI : Fetch data, filters underdogs (+3.5-7.5 road pour spreads, +150-300 ML), AI reco via prompt simple.
Stratégie core : B2B checks, basic stats, contrarian picks sur spreads/ML.
Intégrer Archon pour basic knowledge (e.g., store trends).
Output console/CSV.

10. Phased Roadmap (v1, v2)

v1 : Ajoute agent loop avec memory (past picks) via Pydantic AI, backtesting basic via historical /games et Archon tasks.
v2 : Intègre web_search pour supplements, dashboard Vite.js, upgrade GOAT après MVP test pour boxscores/odds (budget justified pour ROI).
11. Risks & Mitigations

Risk : Limites All-Star (pas advanced) → Mitigation : Proxies basiques + web tools ; upgrade GOAT après MVP si nécessaire (budget ok pour potential returns).
Risk : Rate limits APIs → Mitigation : Caching via Archon, batch