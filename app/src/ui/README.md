# src/ui — hệ component của sản phẩm

**Luật một câu**: màu chỉ đến từ cầu token (`index.css @theme inline`), control chỉ đến từ
`controls.tsx`. Cổng `npm run audit:ui` (chạy trong mọi `pnpm build`) fail khi một chữ ký
control thô (`h-[30px]…`, `bg-brand-600…`, `<select`, surface paper, cỡ chữ px-lẻ) xuất hiện
ngoài thư mục này.

| File | Vai trò |
|---|---|
| `controls.tsx` | Button (primary/secondary/danger · md/sm) · IconButton (tròn) · Select (pill?) · Field · SectionTitle (16) · Surface (2xl) · Notice (ok/error) · Kbd · ProgressBar |
| `AppTabs.tsx` | Nav pill theo hình học ToggleButtonGroup DS (gap: bản registry light-only) |
| `icons.tsx` | Glyph theo hình học DsIcon (gap: DsIcon không tiêu thụ được ngoài repo DOL) |
| `ModelPanel.tsx` · `useShortcut.ts` | Component/hook mức sản phẩm, tiêu thụ kit |

Bậc hình học đã chốt với chủ: chữ 16/14/12 (+18 màn chào) · control 30px `rounded-xl`,
nhỏ 28px `rounded-lg`, icon-button tròn, pill cho nav/ngôn ngữ · surface `rounded-2xl` ·
hover = `wash` (na05) · focus = info blue (`--color-focus`) · destructive = `danger`,
không bao giờ dùng brand.
