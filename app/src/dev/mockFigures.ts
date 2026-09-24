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
function pyramid(): string {
  const note = (y: number, from: number, colour: string, words: string) =>
    `<path d="M${from} ${y}H770" stroke="#B9C3D3" stroke-width="2"/>` +
    `<circle cx="770" cy="${y}" r="6" fill="${colour}"/>` +
    `<text x="788" y="${y + 7}" font-size="19" fill="${MUTED}">${words}</text>`;
  return svg(1200, 800, "Tháp nhu cầu của trải nghiệm", `<defs>
  <linearGradient id="ground" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F8F9FC"/><stop offset="1" stop-color="#ECF0F7"/></linearGradient>
</defs>
<rect width="1200" height="800" fill="url(#ground)"/>
<g font-family="${SANS}">
  <text x="80" y="92" font-size="38" font-weight="700" fill="${INK}">Tháp nhu cầu của trải nghiệm</text>
  <text x="80" y="132" font-size="21" fill="${MUTED}">Mỗi tầng chỉ có nghĩa khi tầng bên dưới đã vững</text>
  <polygon points="80,700 720,700 643.4,578 156.6,578" fill="#1D3D8C"/>
  <polygon points="160.3,572 639.7,572 565,453 235,453" fill="#2C62D0"/>
  <polygon points="238.7,447 561.3,447 486.6,328 313.4,328" fill="#86ABEF"/>
  <polygon points="317.2,322 482.8,322 400,190" fill="#F2B544"/>
  <g text-anchor="middle" font-weight="700">
    <text x="400" y="648" font-size="27" fill="#FFFFFF">Hoạt động được</text>
    <text x="400" y="522" font-size="27" fill="#FFFFFF">Tin cậy</text>
    <text x="400" y="398" font-size="27" fill="#0E214A">Dễ dùng</text>
    <text x="400" y="300" font-size="21" fill="#3B2805">Đáng nhớ</text>
  </g>
  ${note(262, 458, "#F2B544", "Có cảm xúc, khiến người ta quay lại")}
  ${note(387, 537, "#86ABEF", "Làm được việc mà không cần học")}
  ${note(512, 615, "#2C62D0", "Chạy ổn định, không làm mất dữ liệu")}
  ${note(639, 695, "#1D3D8C", "Giải quyết đúng một nhu cầu có thật")}
  <path d="M96 325H520" stroke="#E4665C" stroke-width="3" stroke-dasharray="10 8"/>
  <circle cx="96" cy="325" r="6" fill="#E4665C"/>
  <text font-size="17" font-style="italic" fill="#C2473E"><tspan x="96" y="290">Phần lớn sản phẩm</tspan><tspan x="96" y="312">dừng ở đây</tspan></text>
</g>`);
}

/** 3.5:1 - a panorama: short, wide, with type that needs the lightbox. */
function timeline(): string {
  const steps: Array<[string, string, string, string, string]> = [
    // year, label, colour, tint, icon drawn around (0, 0)
    ["1984", "Chuột và cửa sổ", "#7E8AA0", "#EDF0F5", `<rect x="-13" y="-19" width="26" height="38" rx="13"/><path d="M0 -19V-7"/>`],
    ["1993", "Trình duyệt web", "#5C7BB8", "#E7EDF8", `<circle r="18"/><ellipse rx="8" ry="18"/><path d="M-18 0H18M-15 -9H15M-15 9H15"/>`],
    ["2007", "Chạm đa điểm", "#2F6FDE", "#E3EDFD", `<circle r="4" fill="currentColor"/><circle r="11"/><circle r="18" stroke-opacity=".45"/>`],
    ["2011", "Trợ lý giọng nói", "#1A9E8F", "#DFF3F0", `<rect x="-6" y="-19" width="12" height="22" rx="6"/><path d="M-11 -3a11 11 0 0 0 22 0M0 8V16M-7 16H7"/>`],
    ["2016", "Thực tế ảo", "#E4665C", "#FCE7E5", `<rect x="-20" y="-11" width="40" height="22" rx="9"/><circle cx="-9" r="4.5"/><circle cx="9" r="4.5"/><path d="M-20 -3H-27M20 -3H27"/>`],
    ["2022", "Trò chuyện với AI", "#7B61D9", "#7B61D9", `<path d="M-18 -16h36a6 6 0 0 1 6 6v16a6 6 0 0 1-6 6h-20l-10 8v-8h-6a6 6 0 0 1-6-6v-16a6 6 0 0 1 6-6z"/><path d="M0 -10l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" fill="currentColor"/>`],
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
  return svg(1600, 460, "Ta điều khiển máy tính bằng gì", `<defs>
  <linearGradient id="track" gradientUnits="userSpaceOnUse" x1="100" y1="0" x2="1500" y2="0"><stop offset="0" stop-color="#AEB7C7"/><stop offset=".55" stop-color="#2F6FDE"/><stop offset="1" stop-color="#7B61D9"/></linearGradient>
</defs>
<rect width="1600" height="460" fill="#FBFBFD"/>
<g font-family="${SANS}">
  <text x="80" y="70" font-size="30" font-weight="700" fill="${INK}">Ta điều khiển máy tính bằng gì</text>
  <text x="80" y="104" font-size="19" fill="${MUTED}">Mỗi bước đổi cách con người và máy nói chuyện với nhau</text>
  <path d="M100 300H1502" stroke="url(#track)" stroke-width="4" stroke-linecap="round"/>
  <path d="M1494 290l14 10-14 10" fill="none" stroke="#7B61D9" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
  ${marks}
</g>`);
}

/** 1:1 - a Venn diagram, drawn twice: the book's original and its
 * translated copy, the pair the duplicate rule is about. */
function venn(locale: "en" | "vi"): string {
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

/** About 1:2 - a phone screen, the tallest thing a page has to fit. */
function phone(): string {
  return svg(560, 1160, "Màn hình chào của một ứng dụng đọc", `<defs>
  <linearGradient id="ground" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E7ECF5"/><stop offset="1" stop-color="#F6F7FA"/></linearGradient>
  <linearGradient id="art" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFE6BF"/><stop offset="1" stop-color="#FFC9B5"/></linearGradient>
</defs>
<rect width="560" height="1160" fill="url(#ground)"/>
<rect x="60" y="60" width="440" height="1040" rx="72" fill="#161A22"/>
<rect x="76" y="76" width="408" height="1008" rx="58" fill="#FFFFFF"/>
<rect x="230" y="94" width="100" height="30" rx="15" fill="#161A22"/>
<g font-family="${SANS}">
  <text x="114" y="118" font-size="19" font-weight="700" fill="${INK}">9:41</text>
  <g fill="${INK}"><rect x="384" y="106" width="4" height="10" rx="1"/><rect x="391" y="102" width="4" height="14" rx="1"/><rect x="398" y="98" width="4" height="18" rx="1"/><rect x="416" y="100" width="30" height="15" rx="4" fill="none" stroke="${INK}" stroke-width="2"/><rect x="419" y="103" width="21" height="9" rx="2"/></g>
  <rect x="100" y="170" width="360" height="390" rx="36" fill="url(#art)"/>
  <circle cx="386" cy="246" r="38" fill="#FFB35C"/>
  <g transform="translate(170 250)"><circle r="36" fill="#FFFFFF"/><path d="M0 -20V0l14 10" fill="none" stroke="#E07A4F" stroke-width="5" stroke-linecap="round"/></g>
  <path d="M280 470c-40-22-92-26-128-14v-96c36-12 88-8 128 14z" fill="#FFFFFF" stroke="#E07A4F" stroke-width="4" stroke-linejoin="round"/>
  <path d="M280 470c40-22 92-26 128-14v-96c-36-12-88-8-128 14z" fill="#FFFFFF" stroke="#E07A4F" stroke-width="4" stroke-linejoin="round"/>
  <path d="M176 392h72M176 414h60M312 392h72M312 414h54" stroke="#F3B79F" stroke-width="5" stroke-linecap="round"/>
  <text font-size="38" font-weight="700" fill="${INK}"><tspan x="112" y="636">Mỗi ngày</tspan><tspan x="112" y="682">mười phút đọc</tspan></text>
  <text font-size="21" fill="${MUTED}"><tspan x="112" y="734">Chọn một khung giờ cố định.</tspan><tspan x="112" y="764">Ứng dụng sẽ nhắc đúng lúc.</tspan></text>
  <rect x="112" y="818" width="30" height="10" rx="5" fill="#2F6FDE"/>
  <circle cx="160" cy="823" r="5" fill="#C9D1DD"/>
  <circle cx="178" cy="823" r="5" fill="#C9D1DD"/>
  <rect x="100" y="900" width="360" height="72" rx="36" fill="#2F6FDE"/>
  <text x="280" y="944" text-anchor="middle" font-size="24" font-weight="700" fill="#FFFFFF">Bắt đầu</text>
  <text x="280" y="1022" text-anchor="middle" font-size="21" fill="#2F6FDE">Để sau</text>
</g>
<rect x="210" y="1058" width="140" height="6" rx="3" fill="#161A22"/>`);
}

/** 4:3 - an illustration with no words at all, like a photograph. */
function interview(): string {
  const notes: Array<[number, number, number, string]> = [
    [742, 186, -4, "#FFE27A"], [822, 180, 3, "#FFB3C1"], [902, 188, -2, "#A7D8FF"], [982, 182, 4, "#FFE27A"],
    [746, 268, 2, "#B8F0C8"], [826, 262, -3, "#FFE27A"], [906, 270, 3, "#FFB3C1"],
    [744, 350, -2, "#A7D8FF"], [824, 346, 4, "#B8F0C8"],
    [1062, 262, -3, "#A7D8FF"], [1058, 346, 2, "#FFE27A"],
  ];
  const board = notes.map(([x, y, turn, colour]) =>
    `<g transform="translate(${x} ${y}) rotate(${turn})"><rect x="-32" y="-32" width="64" height="64" rx="4" fill="${colour}"/><path d="M-20 -10H18M-20 4H8" stroke="#1B2233" stroke-opacity=".25" stroke-width="4" stroke-linecap="round"/></g>`,
  ).join("");
  return svg(1200, 900, "Buổi phỏng vấn người dùng", `<defs>
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
function wireframe(): string {
  const pen = `fill="none" stroke="#262626" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"`;
  const red = `fill="none" stroke="#C8372D" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"`;
  const card = (x: number) =>
    `<path d="M${x} 790h190v210H${x}z"/><path d="M${x} 890h190M${x} 790l190 100M${x + 190} 790L${x} 890"/><path d="M${x + 14} 928h160M${x + 14} 954h110" stroke-width="4"/>`;
  return svg(1000, 1180, "Bản phác thảo khung trang chủ", `<g ${pen}>
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
<text x="185" y="728" text-anchor="middle" font-family="${SANS}" font-size="24" fill="#262626">Đăng ký</text>
<g ${red}>
  <path d="M772 318q-30-6-62-2"/><path d="M724 306l-14 10 16 8"/>
  <path d="M772 726q-200 18-472-4"/><path d="M314 712l-14 10 14 10"/>
  <path d="M772 900q-30-4-62 0"/><path d="M724 888l-14 12 16 8"/>
</g>
<g font-family="${SANS}" font-size="24" font-style="italic" fill="#C8372D">
  <text><tspan x="784" y="306">Ảnh lớn:</tspan><tspan x="784" y="336">người thật?</tspan></text>
  <text><tspan x="784" y="712">Chỉ một nút</tspan><tspan x="784" y="742">kêu gọi</tspan></text>
  <text><tspan x="784" y="890">Ba lợi ích</tspan><tspan x="784" y="920">chính</tspan></text>
</g>`);
}

/** Smaller than the column: it must stay its own size, not be blown up. */
function buttonStates(): string {
  const button = (x: number, fill: string, extra: string) =>
    `<rect x="${x}" y="30" width="124" height="46" rx="23" fill="${fill}"/>${extra}`;
  return svg(480, 140, "Ba trạng thái của một nút", `<rect width="480" height="140" rx="12" fill="#F4F6F9"/>
<g font-family="${SANS}">
  ${button(28, "#2F6FDE", `<text x="90" y="59" text-anchor="middle" font-size="18" font-weight="700" fill="#FFFFFF">Lưu</text>`)}
  ${button(178, "#1F4FAE", `<text x="240" y="59" text-anchor="middle" font-size="18" font-weight="700" fill="#FFFFFF">Lưu</text><path d="M282 58v22l6-6 4 10 4-2-4-10h8z" fill="#FFFFFF" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>`)}
  ${button(328, "#8FB2EE", `<circle cx="366" cy="53" r="9" fill="none" stroke="#FFFFFF" stroke-opacity=".45" stroke-width="3"/><path d="M366 44a9 9 0 0 1 9 9" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round"/><text x="402" y="59" text-anchor="middle" font-size="18" font-weight="700" fill="#FFFFFF">Lưu</text>`)}
  <g text-anchor="middle" font-size="14" fill="${MUTED}">
    <text x="90" y="110">Mặc định</text><text x="240" y="110">Rê chuột</text><text x="390" y="110">Đang lưu</text>
  </g>
</g>`);
}

/** 16:9 - a chart: numbers that line up, one bar that matters. */
function funnel(): string {
  const rows: Array<[string, number, string]> = [
    ["Mở trang đăng ký", 100, "#2F6FDE"],
    ["Điền thông tin", 72, "#2F6FDE"],
    ["Xác minh email", 41, "#E4665C"],
    ["Hoàn tất", 33, "#2F6FDE"],
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
  <text x="${362 + value * 8 + drop * 4}" y="${y + 7}" text-anchor="middle" font-size="20" font-weight="700" fill="#C2473E">Mất ${drop} điểm</text>`
      : `<text x="${376 + value * 8}" y="${y + 8}" font-size="22" font-weight="700" fill="${INK}">${value}%</text>`;
    return `<text x="80" y="${y + 8}" font-size="22" fill="${INK}">${label}</text>
  <rect x="360" y="${y - 28}" width="${value * 8}" height="56" rx="10" fill="${colour}"/>
  ${figure}`;
  }).join("\n  ");
  return svg(1280, 720, "Người dùng rời đi ở bước nào", `<rect width="1280" height="720" fill="#FCFCFD"/>
<g font-family="${SANS}">
  <text x="80" y="86" font-size="34" font-weight="700" fill="${INK}">Người dùng rời đi ở bước nào</text>
  <text x="80" y="124" font-size="20" fill="${MUTED}">Tỷ lệ còn lại sau mỗi bước đăng ký · số liệu minh hoạ</text>
  ${grid}
  ${bars}
</g>`);
}

/** Every picture the harness serves, by figure id. */
export function mockFigureSvgs(): Record<string, string> {
  return {
    "fig-wide": pyramid(),
    "fig-timeline": timeline(),
    "fig-sample": venn("en"),
    "fig-sample-vi": venn("vi"),
    "fig-tall": phone(),
    "fig-scene": interview(),
    "fig-lineart": wireframe(),
    "fig-small": buttonStates(),
    "fig-chart": funnel(),
  };
}
