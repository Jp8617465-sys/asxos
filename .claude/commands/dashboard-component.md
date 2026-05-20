# Dashboard Component Task

<context>
- Frontend: Next.js 14 on Vercel, React + TypeScript + Tailwind CSS
- TradeSight AI: Australia's AI Financial Advisor — conversational-first, not dashboard-first
- Contracts: frontend/contracts/ (source of truth for shared types — never duplicate)
- Hooks: frontend/hooks/ (data fetching boundary — snake_case to camelCase mapping HERE ONLY)
- Quality gates: TypeScript strict, ESLint (no-explicit-any: error), Prettier, Jest 80%+
- Target users: Australian retail investors
</context>

<task>
$ARGUMENTS
</task>

<constraints>
- TypeScript strict mode — never `any` (eslint no-explicit-any: error)
- Types defined in frontend/contracts/ — never duplicate
- snake_case → camelCase mapping only in frontend/hooks/ boundary
- Responsive: must work on mobile
- Accessible: WCAG 2.1 AA minimum
- All financial data must show appropriate disclaimers
- Bundle budget: < 200KB gzipped total
</constraints>

<verify>
1. TypeScript compiles with zero errors (npm run type-check)
2. ESLint passes (npm run lint)
3. Component has Jest test with ≥80% coverage
4. Types reference contracts/ — no inline type duplication
5. Renders correctly at mobile breakpoints
</verify>
