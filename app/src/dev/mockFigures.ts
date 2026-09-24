/** The pictures the preview harness puts in its sample book.
 *
 * Drawn to look like the figures real books carry, and chosen so that every
 * SHAPE the reader has to lay out turns up somewhere: a panorama, a wide
 * chart, a 3:2 diagram, a 4:3 illustration, a square, a portrait sketch, a
 * phone screen twice as tall as it is wide, and one picture smaller than the
 * column. One of them has no background of its own, like most line art does.
 * Every picture is self-contained: no fonts, images or requests from outside.
 * Imported only by the DEV mock host, so none of it reaches a build.
 */

type Locale = "vi" | "en";

const SANS = "system-ui, -apple-system, 'Helvetica Neue', Helvetica, Arial, sans-serif";
const INK = "#1B2233";
const MUTED = "#5B6475";

function svg(width: number, height: number, title: string, body: string): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${title}">
<title>${title}</title>
${body}
</svg>`;
}

/** 3:2 - a diagram with words inside and beside it. */
function pyramid(locale: Locale): string {
  const w = locale === "en"
    ? { title: "The hierarchy of experience", note: "Each level only counts once the one below it holds",
        tiers: ["Functional", "Reliable", "Usable", "Memorable"],
        why: ["Solves a need that is real", "Works every time, loses nothing", "Does the job without a manual", "Makes people want to come back"],
        stop: ["Most products", "stop here"] }
    : { title: "Tháp nhu cầu của trải nghiệm", note: "Mỗi tầng chỉ có nghĩa khi tầng bên dưới đã vững",
        tiers: ["Hoạt động được", "Tin cậy", "Dễ dùng", "Đáng nhớ"],
        why: ["Giải quyết đúng một nhu cầu có thật", "Chạy ổn định, không làm mất dữ liệu", "Làm được việc mà không cần học", "Có cảm xúc, khiến người ta quay lại"],
        stop: ["Phần lớn sản phẩm", "dừng ở đây"] };
  const note = (y: number, from: number, colour: string, words: string) =>
    `<path d="M${from} ${y}H770" stroke="#B9C3D3" stroke-width="2"/>` +
    `<circle cx="770" cy="${y}" r="6" fill="${colour}"/>` +
    `<text x="788" y="${y + 7}" font-size="19" fill="${MUTED}">${words}</text>`;
  return svg(1200, 800, w.title, `<defs>
  <linearGradient id="ground" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F8F9FC"/><stop offset="1" stop-color="#ECF0F7"/></linearGradient>
</defs>
<rect width="1200" height="800" fill="url(#ground)"/>
<g font-family="${SANS}">
  <text x="80" y="92" font-size="38" font-weight="700" fill="${INK}">${w.title}</text>
  <text x="80" y="132" font-size="21" fill="${MUTED}">${w.note}</text>
  <polygon points="80,700 720,700 643.4,578 156.6,578" fill="#1D3D8C"/>
  <polygon points="160.3,572 639.7,572 565,453 235,453" fill="#2C62D0"/>
  <polygon points="238.7,447 561.3,447 486.6,328 313.4,328" fill="#86ABEF"/>
  <polygon points="317.2,322 482.8,322 400,190" fill="#F2B544"/>
  <g text-anchor="middle" font-weight="700">
    <text x="400" y="648" font-size="27" fill="#FFFFFF">${w.tiers[0]}</text>
    <text x="400" y="522" font-size="27" fill="#FFFFFF">${w.tiers[1]}</text>
    <text x="400" y="398" font-size="27" fill="#0E214A">${w.tiers[2]}</text>
    <text x="400" y="300" font-size="21" fill="#3B2805">${w.tiers[3]}</text>
  </g>
  ${note(262, 458, "#F2B544", w.why[3])}
  ${note(387, 537, "#86ABEF", w.why[2])}
  ${note(512, 615, "#2C62D0", w.why[1])}
  ${note(639, 695, "#1D3D8C", w.why[0])}
  <path d="M96 325H520" stroke="#E4665C" stroke-width="3" stroke-dasharray="10 8"/>
  <circle cx="96" cy="325" r="6" fill="#E4665C"/>
  <text font-size="17" font-style="italic" fill="#C2473E"><tspan x="96" y="290">${w.stop[0]}</tspan><tspan x="96" y="312">${w.stop[1]}</tspan></text>
</g>`);
}

/** 3.5:1 - a panorama: short, wide, with type that needs the lightbox. */
function timeline(locale: Locale): string {
  const en = locale === "en";
  const w = en
    ? { title: "How we tell computers what to do", note: "Each step changed how people and machines talk to each other",
        labels: ["Mouse and windows", "The web browser", "Multi-touch", "Voice assistants", "Virtual reality", "Chatting with AI"] }
    : { title: "Ta điều khiển máy tính bằng gì", note: "Mỗi bước đổi cách con người và máy nói chuyện với nhau",
        labels: ["Chuột và cửa sổ", "Trình duyệt web", "Chạm đa điểm", "Trợ lý giọng nói", "Thực tế ảo", "Trò chuyện với AI"] };
  const steps: Array<[string, string, string, string, string]> = [
    // year, label, colour, tint, icon drawn around (0, 0)
    ["1984", w.labels[0], "#7E8AA0", "#EDF0F5", `<rect x="-13" y="-19" width="26" height="38" rx="13"/><path d="M0 -19V-7"/>`],
    ["1993", w.labels[1], "#5C7BB8", "#E7EDF8", `<circle r="18"/><ellipse rx="8" ry="18"/><path d="M-18 0H18M-15 -9H15M-15 9H15"/>`],
    ["2007", w.labels[2], "#2F6FDE", "#E3EDFD", `<circle r="4" fill="currentColor"/><circle r="11"/><circle r="18" stroke-opacity=".45"/>`],
    ["2011", w.labels[3], "#1A9E8F", "#DFF3F0", `<rect x="-6" y="-19" width="12" height="22" rx="6"/><path d="M-11 -3a11 11 0 0 0 22 0M0 8V16M-7 16H7"/>`],
    ["2016", w.labels[4], "#E4665C", "#FCE7E5", `<rect x="-20" y="-11" width="40" height="22" rx="9"/><circle cx="-9" r="4.5"/><circle cx="9" r="4.5"/><path d="M-20 -3H-27M20 -3H27"/>`],
    ["2022", w.labels[5], "#7B61D9", "#7B61D9", `<path d="M-18 -16h36a6 6 0 0 1 6 6v16a6 6 0 0 1-6 6h-20l-10 8v-8h-6a6 6 0 0 1-6-6v-16a6 6 0 0 1 6-6z"/><path d="M0 -10l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" fill="currentColor"/>`],
  ];
  const marks = steps.map(([year, label, colour, tint, icon], index) => {
    const x = 170 + index * 252;
    const last = index === steps.length - 1;
    const stroke = last ? "#FFFFFF" : colour;
    return `<circle cx="${x}" cy="210" r="42" fill="${tint}" stroke="${colour}" stroke-width="3"/>
  <g transform="translate(${x} 210)" fill="none" stroke="${stroke}" color="${stroke}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">${icon}</g>
  <path d="M${x} 252V290" stroke="${colour}" stroke-width="2"/>
  <circle cx="${x}" cy="300" r="9" fill="${colour}" stroke="#FBFBFD" stroke-width="4"/>
  <text x="${x}" y="356" text-anchor="middle" font-size="32" font-weight="700" fill="${INK}">${year}</text>
  <text x="${x}" y="392" text-anchor="middle" font-size="21" fill="${MUTED}">${label}</text>`;
  }).join("\n  ");
  return svg(1600, 460, w.title, `<defs>
  <linearGradient id="track" gradientUnits="userSpaceOnUse" x1="100" y1="0" x2="1500" y2="0"><stop offset="0" stop-color="#AEB7C7"/><stop offset=".55" stop-color="#2F6FDE"/><stop offset="1" stop-color="#7B61D9"/></linearGradient>
</defs>
<rect width="1600" height="460" fill="#FBFBFD"/>
<g font-family="${SANS}">
  <text x="80" y="70" font-size="30" font-weight="700" fill="${INK}">${w.title}</text>
  <text x="80" y="104" font-size="19" fill="${MUTED}">${w.note}</text>
  <path d="M100 300H1502" stroke="url(#track)" stroke-width="4" stroke-linecap="round"/>
  <path d="M1494 290l14 10-14 10" fill="none" stroke="#7B61D9" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
  ${marks}
</g>`);
}

/** 1:1 - a Venn diagram, drawn twice: the book's original and its
 * translated copy, the pair the duplicate rule is about. */
function venn(locale: Locale): string {
  const en = locale === "en";
  const words = en
    ? { title: "Three paths into UX", note: "Most people come from a neighbouring craft", a: ["Web and", "software"], b: ["Graphic and", "print"], c: ["Research and", "psychology"] }
    : { title: "Ba con đường vào UX", note: "Phần lớn đến từ một nghề gần đó", a: ["Web và", "phần mềm"], b: ["Đồ hoạ và", "in ấn"], c: ["Nghiên cứu và", "tâm lý học"] };
  const label = (x: number, y: number, lines: string[]) =>
    `<text x="${x}" text-anchor="middle" font-size="28" font-weight="700" fill="${INK}"><tspan x="${x}" y="${y}">${lines[0]}</tspan><tspan x="${x}" y="${y + 34}">${lines[1]}</tspan></text>`;
  return svg(1000, 1000, words.title, `<rect width="1000" height="1000" fill="#FAFAF8"/>
<g font-family="${SANS}">
  <text x="500" y="96" text-anchor="middle" font-size="40" font-weight="700" fill="${INK}">${words.title}</text>
  <text x="500" y="138" text-anchor="middle" font-size="22" fill="${MUTED}">${words.note}</text>
  <g stroke-width="3" stroke-opacity=".55" fill-opacity=".2">
    <circle cx="385" cy="455" r="235" fill="#2F6FDE" stroke="#2F6FDE"/>
    <circle cx="615" cy="455" r="235" fill="#E4665C" stroke="#E4665C"/>
    <circle cx="500" cy="655" r="235" fill="#1A9E8F" stroke="#1A9E8F"/>
  </g>
  <g fill="none" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">
    <path transform="translate(290 345)" stroke="#2F6FDE" d="M-14 -12L-26 0l12 12M14 -12L26 0 14 12M6 -16l-12 32"/>
    <path transform="translate(710 345)" stroke="#E4665C" d="M0 -20l14 28L0 20l-14-12zM0 -20V2"/>
    <g transform="translate(500 750)" stroke="#1A9E8F"><circle cx="-4" cy="-4" r="14"/><path d="M6 6l12 12"/></g>
  </g>
  ${label(290, 400, words.a)}
  ${label(710, 400, words.b)}
  ${label(500, 806, words.c)}
  <circle cx="500" cy="522" r="52" fill="${INK}"/>
  <text x="500" y="535" text-anchor="middle" font-size="34" font-weight="700" fill="#FFFFFF">UX</text>
</g>`);
}

/** About 1:2 - a phone screen, the tallest thing a page has to fit. Drawn
 * the way product books show one: a thin-bezel device lifted off a soft
 * ground, and a screen that tells its own story - the reminder the copy
 * promises is sitting right there on it. */
function phone(locale: Locale): string {
  const w = locale === "en"
    ? { title: "The welcome screen of a reading app", head: ["Ten minutes", "of reading a day"], body: ["Pick one fixed time each day.", "The app will remind you."], ping: ["Time to read", "Your ten minutes start now"], go: "Get started", later: "Not now" }
    : { title: "Màn hình chào của một ứng dụng đọc", head: ["Mỗi ngày", "mười phút đọc"], body: ["Chọn một khung giờ cố định.", "Ứng dụng sẽ nhắc đúng lúc."], ping: ["Đến giờ đọc rồi", "Mười phút của bạn bắt đầu"], go: "Bắt đầu", later: "Để sau" };
  const book = (x: number, y: number, width: number, height: number, colour: string, band: string, label: number) =>
    `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="6" fill="${colour}"/>` +
    `<rect x="${x + 12}" y="${y}" width="6" height="${height}" fill="${band}"/>` +
    `<rect x="${x + 30}" y="${y + height / 2 - 3.5}" width="${label}" height="7" rx="3.5" fill="#FFFFFF" fill-opacity=".6"/>` +
    `<rect x="${x + width - 12}" y="${y + 4}" width="7" height="${height - 8}" rx="2" fill="#FFF6E5"/>`;
  return svg(600, 1160, w.title, `<defs>
  <linearGradient id="ground" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#EEF1F8"/><stop offset="1" stop-color="#E2E7F1"/></linearGradient>
  <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#E7EEFF"/><stop offset="1" stop-color="#F5EDFF"/></linearGradient>
  <radialGradient id="sun" cx=".4" cy=".35" r=".7"><stop offset="0" stop-color="#FFE4A8"/><stop offset="1" stop-color="#FFB45A"/></radialGradient>
  <filter id="haze" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="46"/></filter>
  <filter id="lift" x="-30%" y="-20%" width="160%" height="150%"><feDropShadow dx="0" dy="26" stdDeviation="26" flood-color="#1B2233" flood-opacity=".24"/></filter>
  <filter id="float" x="-20%" y="-50%" width="140%" height="220%"><feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#1B2233" flood-opacity=".14"/></filter>
</defs>
<rect width="600" height="1160" fill="url(#ground)"/>
<g filter="url(#haze)"><circle cx="110" cy="250" r="150" fill="#D3E0FF"/><circle cx="520" cy="890" r="170" fill="#FFE0CF"/></g>
<g filter="url(#lift)"><rect x="70" y="100" width="460" height="960" rx="78" fill="#15181E"/></g>
<rect x="71.5" y="101.5" width="457" height="957" rx="76.5" fill="none" stroke="#353B47" stroke-width="3"/>
<g fill="#15181E"><rect x="63" y="268" width="8" height="44" rx="3"/><rect x="63" y="336" width="8" height="78" rx="3"/><rect x="63" y="430" width="8" height="78" rx="3"/><rect x="529" y="372" width="8" height="118" rx="3"/></g>
<rect x="84" y="114" width="432" height="932" rx="64" fill="#FFFFFF"/>
<rect x="254" y="132" width="92" height="28" rx="14" fill="#0B0D11"/>
<g font-family="${SANS}">
  <text x="126" y="155" font-size="19" font-weight="600" fill="${INK}">9:41</text>
  <g fill="${INK}"><rect x="410" y="148" width="4" height="7" rx="1.5"/><rect x="416" y="145" width="4" height="10" rx="1.5"/><rect x="422" y="142" width="4" height="13" rx="1.5"/><rect x="428" y="139" width="4" height="16" rx="1.5"/></g>
  <path d="M441.2 145.2A11 11 0 0 1 456.8 145.2M444.4 148.4A6.5 6.5 0 0 1 453.6 148.4" fill="none" stroke="${INK}" stroke-width="2.4" stroke-linecap="round"/>
  <circle cx="449" cy="152.5" r="2" fill="${INK}"/>
  <rect x="465" y="141" width="27" height="14" rx="4.5" fill="none" stroke="${INK}" stroke-opacity=".4" stroke-width="2"/>
  <rect x="467.5" y="143.5" width="18" height="9" rx="2.5" fill="${INK}"/>
  <path d="M495 146.5v3.5" stroke="${INK}" stroke-opacity=".4" stroke-width="2" stroke-linecap="round"/>
  <rect x="108" y="186" width="384" height="410" rx="32" fill="url(#panel)"/>
  <circle cx="392" cy="282" r="56" fill="url(#sun)"/>
  <g fill="#FFFFFF" fill-opacity=".92"><rect x="148" y="240" width="96" height="26" rx="13"/><rect x="174" y="224" width="52" height="30" rx="15"/><rect x="322" y="318" width="84" height="22" rx="11"/><rect x="344" y="305" width="40" height="24" rx="12"/></g>
  <rect x="132" y="528" width="336" height="12" rx="6" fill="#D3DCF2"/>
  <path d="M150 478h40l-6 50h-28z" fill="#E07A5F"/>
  <rect x="145" y="470" width="50" height="11" rx="4" fill="#C8644A"/>
  <g fill="#3E9C6E"><ellipse cx="158" cy="436" rx="10" ry="30" transform="rotate(-28 158 436)"/><ellipse cx="184" cy="432" rx="10" ry="32" transform="rotate(24 184 432)"/></g>
  <ellipse cx="170" cy="422" rx="10" ry="38" fill="#58B384"/>
  ${book(214, 490, 190, 38, "#2F6FDE", "#1F4FAE", 70)}
  ${book(228, 456, 164, 34, "#F2B544", "#D9982A", 56)}
  ${book(218, 424, 176, 32, "#7B61D9", "#6147C0", 62)}
  <rect x="418" y="478" width="44" height="50" rx="10" fill="#FFFFFF" stroke="#CFD8EC" stroke-width="3"/>
  <path d="M462 490q15 0 15 13t-15 13" fill="none" stroke="#CFD8EC" stroke-width="4"/>
  <path d="M432 466q-7-11 0-22M448 466q-7-11 0-22" fill="none" stroke="#C3CDE6" stroke-width="3.5" stroke-linecap="round"/>
  <g filter="url(#float)"><rect x="124" y="556" width="352" height="86" rx="22" fill="#FFFFFF"/></g>
  <rect x="142" y="575" width="48" height="48" rx="12" fill="#2F6FDE"/>
  <path d="M166 591c-5-3.5-11-4.5-16-3.5v19c5-1 11 0 16 3.5zM166 591c5-3.5 11-4.5 16-3.5v19c-5-1-11 0-16 3.5z" fill="#FFFFFF"/>
  <text x="204" y="594" font-size="18" font-weight="700" fill="${INK}">${w.ping[0]}</text>
  <text x="204" y="618" font-size="15.5" fill="${MUTED}">${w.ping[1]}</text>
  <text x="458" y="594" text-anchor="end" font-size="14" fill="#8A93A6">8:00</text>
  <text font-size="36" font-weight="700" letter-spacing="-.4" fill="#141A26"><tspan x="112" y="712">${w.head[0]}</tspan><tspan x="112" y="756">${w.head[1]}</tspan></text>
  <text font-size="19.5" fill="${MUTED}"><tspan x="112" y="804">${w.body[0]}</tspan><tspan x="112" y="832">${w.body[1]}</tspan></text>
  <rect x="112" y="872" width="26" height="8" rx="4" fill="#2F6FDE"/>
  <circle cx="150" cy="876" r="4" fill="#CBD3E1"/>
  <circle cx="164" cy="876" r="4" fill="#CBD3E1"/>
  <rect x="108" y="908" width="384" height="62" rx="31" fill="#2F6FDE"/>
  <text x="300" y="946" text-anchor="middle" font-size="21" font-weight="700" fill="#FFFFFF">${w.go}</text>
  <text x="300" y="1004" text-anchor="middle" font-size="18.5" font-weight="600" fill="#2F6FDE">${w.later}</text>
</g>
<rect x="234" y="1026" width="132" height="5" rx="2.5" fill="#15181E"/>`);
}

/** 4:3 - an illustration with no words at all, like a photograph. */
function interview(locale: Locale): string {
  const notes: Array<[number, number, number, string]> = [
    [742, 186, -4, "#FFE27A"], [822, 180, 3, "#FFB3C1"], [902, 188, -2, "#A7D8FF"], [982, 182, 4, "#FFE27A"],
    [746, 268, 2, "#B8F0C8"], [826, 262, -3, "#FFE27A"], [906, 270, 3, "#FFB3C1"],
    [744, 350, -2, "#A7D8FF"], [824, 346, 4, "#B8F0C8"],
    [1062, 262, -3, "#A7D8FF"], [1058, 346, 2, "#FFE27A"],
  ];
  const board = notes.map(([x, y, turn, colour]) =>
    `<g transform="translate(${x} ${y}) rotate(${turn})"><rect x="-32" y="-32" width="64" height="64" rx="4" fill="${colour}"/><path d="M-20 -10H18M-20 4H8" stroke="#1B2233" stroke-opacity=".25" stroke-width="4" stroke-linecap="round"/></g>`,
  ).join("");
  return svg(1200, 900, locale === "en" ? "A user interview" : "Buổi phỏng vấn người dùng", `<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9FD3F0"/><stop offset="1" stop-color="#E4F4FB"/></linearGradient>
  <linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E4EDE7"/><stop offset="1" stop-color="#D8E4DC"/></linearGradient>
  <radialGradient id="glow" cx="600" cy="170" r="420" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#FFF1C7" stop-opacity=".9"/><stop offset="1" stop-color="#FFF1C7" stop-opacity="0"/></radialGradient>
</defs>
<rect width="1200" height="900" fill="url(#wall)"/>
<rect y="700" width="1200" height="200" fill="#C3D3C9"/>
<path d="M0 700H1200" stroke="#AFC2B6" stroke-width="6"/>
<rect x="90" y="110" width="300" height="360" rx="14" fill="#FFFFFF"/>
<rect x="106" y="126" width="268" height="328" rx="6" fill="url(#sky)"/>
<circle cx="300" cy="200" r="30" fill="#FFF3B0"/>
<path d="M106 400q60-50 120-20t148-30v104H106z" fill="#9CC9A8"/>
<path d="M106 430q80-40 170-10t98-6v40H106z" fill="#7DB592"/>
<path d="M240 126V454M106 290H374" stroke="#FFFFFF" stroke-width="10"/>
<rect x="690" y="124" width="420" height="300" rx="10" fill="#FFFFFF" stroke="#CFD8D2" stroke-width="3"/>
${board}
<ellipse cx="866" cy="266" rx="92" ry="50" transform="rotate(-3 866 266)" fill="none" stroke="#2F6FDE" stroke-width="4"/>
<rect x="700" y="424" width="400" height="12" rx="6" fill="#CFD8D2"/>
<rect width="1200" height="700" fill="url(#glow)"/>
<path d="M600 0V140" stroke="#3A4150" stroke-width="3"/>
<path d="M556 176a44 36 0 0 1 88 0z" fill="#F2B544"/>
<rect x="250" y="410" width="30" height="210" rx="10" fill="#4A5366"/>
<rect x="918" y="404" width="30" height="216" rx="10" fill="#4A5366"/>
<g fill="#4A5366"><rect x="256" y="610" width="12" height="200" rx="4"/><rect x="356" y="610" width="12" height="200" rx="4"/><rect x="832" y="610" width="12" height="200" rx="4"/><rect x="932" y="610" width="12" height="200" rx="4"/></g>
<g fill="#2B3445"><rect x="300" y="596" width="150" height="44" rx="22"/><rect x="414" y="618" width="40" height="172" rx="18"/></g>
<rect x="410" y="778" width="70" height="24" rx="12" fill="#1B2233"/>
<g fill="#3D3A52"><rect x="750" y="596" width="150" height="44" rx="22"/><rect x="746" y="618" width="40" height="172" rx="18"/></g>
<rect x="720" y="778" width="70" height="24" rx="12" fill="#1B2233"/>
<circle cx="341" cy="380" r="45" fill="#3A2A22"/>
<rect x="286" y="430" width="120" height="170" rx="46" fill="#2F6FDE"/>
<circle cx="352" cy="394" r="38" fill="#F1C7A5"/>
<circle cx="374" cy="390" r="3.5" fill="#3A2A22"/>
<path d="M378 476q46 44 92 62" fill="none" stroke="#2F6FDE" stroke-width="28" stroke-linecap="round"/>
<circle cx="474" cy="540" r="13" fill="#F1C7A5"/>
<circle cx="861" cy="374" r="45" fill="#1E1712"/>
<circle cx="890" cy="336" r="18" fill="#1E1712"/>
<rect x="796" y="428" width="120" height="172" rx="46" fill="#E4665C"/>
<circle cx="850" cy="390" r="38" fill="#8D5A3B"/>
<circle cx="828" cy="386" r="3.5" fill="#1E1712"/>
<path d="M820 476q-34 40-62 60" fill="none" stroke="#E4665C" stroke-width="28" stroke-linecap="round"/>
<circle cx="756" cy="538" r="13" fill="#8D5A3B"/>
<path d="M436 552H566L602 470" fill="none" stroke="#8C96A8" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>
<rect x="714" y="516" width="36" height="40" rx="7" fill="#FFFFFF" stroke="#D5DCE6" stroke-width="3"/>
<path d="M750 526q16 0 16 12t-16 12" fill="none" stroke="#D5DCE6" stroke-width="4"/>
<path d="M724 506q-8-12 0-22M738 506q-8-12 0-22" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round"/>
<rect x="230" y="556" width="740" height="26" rx="13" fill="#C08457"/>
<rect x="250" y="582" width="700" height="40" fill="#A96E45"/>
<rect x="290" y="622" width="22" height="200" fill="#8E5A38"/>
<rect x="888" y="622" width="22" height="200" fill="#8E5A38"/>
<path d="M1062 720l14 120h56l14-120z" fill="#3A4A5E"/>
<g fill="#3E9C6E"><ellipse cx="1080" cy="660" rx="18" ry="58" transform="rotate(-24 1080 660)"/><ellipse cx="1124" cy="650" rx="18" ry="64" transform="rotate(20 1124 650)"/></g>
<g fill="#58B384"><ellipse cx="1104" cy="640" rx="16" ry="72"/><ellipse cx="1058" cy="690" rx="14" ry="42" transform="rotate(-52 1058 690)"/><ellipse cx="1150" cy="690" rx="14" ry="42" transform="rotate(52 1150 690)"/></g>`);
}

/** About 5:6 - pen on nothing: a sketch with NO background, the way line
 * art is usually shipped. On a dark page its lines sit on the page itself. */
function wireframe(locale: Locale): string {
  const w = locale === "en"
    ? { title: "A wireframe sketch of a homepage", button: "Sign up", notes: [["Big photo:", "real people?"], ["Only one", "call to action"], ["Three key", "benefits"]] }
    : { title: "Bản phác thảo khung trang chủ", button: "Đăng ký", notes: [["Ảnh lớn:", "người thật?"], ["Chỉ một nút", "kêu gọi"], ["Ba lợi ích", "chính"]] };
  const pen = `fill="none" stroke="#262626" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"`;
  const red = `fill="none" stroke="#C8372D" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"`;
  const card = (x: number) =>
    `<path d="M${x} 790h190v210H${x}z"/><path d="M${x} 890h190M${x} 790l190 100M${x + 190} 790L${x} 890"/><path d="M${x + 14} 928h160M${x + 14} 954h110" stroke-width="4"/>`;
  return svg(1000, 1180, w.title, `<g ${pen}>
  <path d="M44 40q348-4 694 2 6 548 2 1096-348 6-696 2-6-550 0-1100z"/>
  <path d="M42 92q348 3 697-1"/>
  <circle cx="72" cy="66" r="7"/><circle cx="96" cy="66" r="7"/><circle cx="120" cy="66" r="7"/>
  <rect x="150" y="54" width="460" height="26" rx="13"/>
  <circle cx="98" cy="140" r="20"/><path d="M88 142q10-12 20 0"/>
  <path d="M500 140h52M580 140h52M660 140h44"/>
  <path d="M80 190h620v280H80z"/><path d="M80 190l620 280M700 190L80 470"/>
  <path d="M80 530h440M80 562h340" stroke-width="12"/>
  <path d="M80 606h580M80 632h560M80 658h440" stroke-width="4"/>
  <rect x="80" y="690" width="210" height="58" rx="29"/>
  ${card(80)}${card(290)}${card(500)}
  <path d="M80 1066h620" stroke-dasharray="14 12"/>
</g>
<text x="185" y="728" text-anchor="middle" font-family="${SANS}" font-size="24" fill="#262626">${w.button}</text>
<g ${red}>
  <path d="M772 318q-30-6-62-2"/><path d="M724 306l-14 10 16 8"/>
  <path d="M772 726q-200 18-472-4"/><path d="M314 712l-14 10 14 10"/>
  <path d="M772 900q-30-4-62 0"/><path d="M724 888l-14 12 16 8"/>
</g>
<g font-family="${SANS}" font-size="24" font-style="italic" fill="#C8372D">
  <text><tspan x="784" y="306">${w.notes[0][0]}</tspan><tspan x="784" y="336">${w.notes[0][1]}</tspan></text>
  <text><tspan x="784" y="712">${w.notes[1][0]}</tspan><tspan x="784" y="742">${w.notes[1][1]}</tspan></text>
  <text><tspan x="784" y="890">${w.notes[2][0]}</tspan><tspan x="784" y="920">${w.notes[2][1]}</tspan></text>
</g>`);
}

/** Smaller than the column: it must stay its own size, not be blown up. */
function buttonStates(locale: Locale): string {
  const w = locale === "en"
    ? { title: "Three states of a button", save: "Save", states: ["Default", "Hover", "Saving"] }
    : { title: "Ba trạng thái của một nút", save: "Lưu", states: ["Mặc định", "Rê chuột", "Đang lưu"] };
  const button = (x: number, fill: string, extra: string) =>
    `<rect x="${x}" y="30" width="124" height="46" rx="23" fill="${fill}"/>${extra}`;
  return svg(480, 140, w.title, `<rect width="480" height="140" rx="12" fill="#F4F6F9"/>
<g font-family="${SANS}">
  ${button(28, "#2F6FDE", `<text x="90" y="59" text-anchor="middle" font-size="18" font-weight="700" fill="#FFFFFF">${w.save}</text>`)}
  ${button(178, "#1F4FAE", `<text x="240" y="59" text-anchor="middle" font-size="18" font-weight="700" fill="#FFFFFF">${w.save}</text><path d="M282 58v22l6-6 4 10 4-2-4-10h8z" fill="#FFFFFF" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>`)}
  ${button(328, "#8FB2EE", `<circle cx="366" cy="53" r="9" fill="none" stroke="#FFFFFF" stroke-opacity=".45" stroke-width="3"/><path d="M366 44a9 9 0 0 1 9 9" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round"/><text x="402" y="59" text-anchor="middle" font-size="18" font-weight="700" fill="#FFFFFF">${w.save}</text>`)}
  <g text-anchor="middle" font-size="14" fill="${MUTED}">
    <text x="90" y="110">${w.states[0]}</text><text x="240" y="110">${w.states[1]}</text><text x="390" y="110">${w.states[2]}</text>
  </g>
</g>`);
}

/** 16:9 - a chart: numbers that line up, one bar that matters. */
function funnel(locale: Locale): string {
  const w = locale === "en"
    ? { title: "Where people drop off", note: "Share still with us after each sign-up step · illustrative numbers", steps: ["Open sign-up page", "Fill in details", "Verify email", "Done"], lost: "Lost" , points: "points" }
    : { title: "Người dùng rời đi ở bước nào", note: "Tỷ lệ còn lại sau mỗi bước đăng ký · số liệu minh hoạ", steps: ["Mở trang đăng ký", "Điền thông tin", "Xác minh email", "Hoàn tất"], lost: "Mất", points: "điểm" };
  const rows: Array<[string, number, string]> = [
    [w.steps[0], 100, "#2F6FDE"],
    [w.steps[1], 72, "#2F6FDE"],
    [w.steps[2], 41, "#E4665C"],
    [w.steps[3], 33, "#2F6FDE"],
  ];
  const grid = [0, 25, 50, 75, 100].map((step) => {
    const x = 360 + step * 8;
    return `<path d="M${x} 186V574" stroke="#E6EAF0" stroke-width="2"/><text x="${x}" y="606" text-anchor="middle" font-size="16" fill="${MUTED}">${step}%</text>`;
  }).join("");
  const bars = rows.map(([label, value, colour], index) => {
    const y = 230 + index * 100;
    const drop = index > 0 && colour !== "#2F6FDE" ? rows[index - 1][1] - value : 0;
    const figure = drop
      ? `<text x="${344 + value * 8}" y="${y + 8}" text-anchor="end" font-size="22" font-weight="700" fill="#FFFFFF">${value}%</text>
  <rect x="${366 + value * 8}" y="${y - 27}" width="${drop * 8 - 8}" height="54" rx="10" fill="#FDF0EE" stroke="#E4665C" stroke-width="2" stroke-dasharray="7 6"/>
  <text x="${362 + value * 8 + drop * 4}" y="${y + 7}" text-anchor="middle" font-size="20" font-weight="700" fill="#C2473E">${w.lost} ${drop} ${w.points}</text>`
      : `<text x="${376 + value * 8}" y="${y + 8}" font-size="22" font-weight="700" fill="${INK}">${value}%</text>`;
    return `<text x="80" y="${y + 8}" font-size="22" fill="${INK}">${label}</text>
  <rect x="360" y="${y - 28}" width="${value * 8}" height="56" rx="10" fill="${colour}"/>
  ${figure}`;
  }).join("\n  ");
  return svg(1280, 720, w.title, `<rect width="1280" height="720" fill="#FCFCFD"/>
<g font-family="${SANS}">
  <text x="80" y="86" font-size="34" font-weight="700" fill="${INK}">${w.title}</text>
  <text x="80" y="124" font-size="20" fill="${MUTED}">${w.note}</text>
  ${grid}
  ${bars}
</g>`);
}

/** Every picture the harness serves, by figure id: the Vietnamese sample
 * book's set, then the English one's (`en-` ids) - the same drawings with
 * their words in the book's own language, as a translated edition has them. */
export function mockFigureSvgs(): Record<string, string> {
  return {
    "fig-wide": pyramid("vi"),
    "fig-timeline": timeline("vi"),
    "fig-sample": venn("en"),
    "fig-sample-vi": venn("vi"),
    "fig-tall": phone("vi"),
    "fig-scene": interview("vi"),
    "fig-lineart": wireframe("vi"),
    "fig-small": buttonStates("vi"),
    "fig-chart": funnel("vi"),
    "en-fig-wide": pyramid("en"),
    "en-fig-timeline": timeline("en"),
    "en-fig-venn": venn("en"),
    "en-fig-tall": phone("en"),
    "en-fig-scene": interview("en"),
    "en-fig-lineart": wireframe("en"),
    "en-fig-small": buttonStates("en"),
    "en-fig-chart": funnel("en"),
  };
}
