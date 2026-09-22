/** Authored document artwork for public demo captures, not a UI component.
 * No external assets, fonts or requests. Imported only by the DEV mock host.
 */
export function showcaseFigureSvg(locale: "vi" | "en"): string {
  const vi = locale === "vi";
  const labels = vi
    ? ["Kỹ thuật", "Thiết kế", "Nghiên cứu"]
    : ["Engineering", "Design", "Research"];
  const notes = vi
    ? ["Biến ý tưởng thành hiện thực", "Dẫn dắt bằng chữ và hình", "Bắt đầu từ con người"]
    : ["Make ideas work", "Give ideas a clear form", "Start with people"];
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="680" viewBox="0 0 1200 680" role="img" aria-labelledby="title desc">
  <title id="title">${vi ? "Ba góc nhìn, một trải nghiệm" : "Three perspectives. One experience."}</title>
  <desc id="desc">${labels.join(" · ")}</desc>
  <rect width="1200" height="680" rx="30" fill="#F3F5FC"/>
  <g font-family="Arial, sans-serif" fill="#202B43">
    <text x="64" y="80" font-size="18" letter-spacing="3" fill="#586888">${vi ? "GÓC NHÌN THIẾT KẾ" : "DESIGN PERSPECTIVES"}</text>
    <text x="64" y="140" font-size="40" font-weight="600">${vi ? "Ba góc nhìn, một trải nghiệm." : "Three perspectives. One experience."}</text>
    <g transform="translate(238 315)">
      <circle r="118" fill="#DEE5FF"/>
      <g transform="rotate(-8)" fill="none" stroke="#4B64CF" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">
        <rect x="-76" y="-60" width="152" height="120" rx="12" fill="#F8FAFF"/>
        <path d="M-76-28H76M-55-44h1m14 0h1m14 0h1M-27-4-45 14l18 18M27-4l18 18-18 18M7-7-7 36"/>
      </g>
      <circle cx="86" cy="78" r="28" fill="#4B64CF"/>
      <text x="86" y="86" text-anchor="middle" fill="#FFF" font-size="22">01</text>
    </g>
    <g transform="translate(600 315)">
      <circle r="118" fill="#DCEFF3"/>
      <g transform="rotate(8)">
        <rect x="-65" y="-76" width="130" height="152" rx="9" fill="#F8FCFD" stroke="#387F91" stroke-width="4"/>
        <circle cx="-20" cy="-25" r="27" fill="#88C8D5"/>
        <path d="M-6 1 26-50 54 1Z" fill="#387F91"/>
        <path d="M-39 30H39M-39 46H22" fill="none" stroke="#387F91" stroke-width="5" stroke-linecap="round"/>
      </g>
      <circle cx="86" cy="78" r="28" fill="#387F91"/>
      <text x="86" y="86" text-anchor="middle" fill="#FFF" font-size="22">02</text>
    </g>
    <g transform="translate(962 315)">
      <circle r="118" fill="#DEE5FF"/>
      <path d="M-66-32 0 20 65-42M0 20 52 76" fill="none" stroke="#A5B5EC" stroke-width="4"/>
      <circle cx="-66" cy="-32" r="18" fill="#A5B5EC"/>
      <circle cx="65" cy="-42" r="24" fill="#A5B5EC"/>
      <circle cx="52" cy="76" r="13" fill="#A5B5EC"/>
      <circle cy="20" r="51" fill="#F8FAFF" stroke="#4B64CF" stroke-width="4"/>
      <circle cy="7" r="14" fill="#4B64CF"/>
      <path d="M-26 43c0-27 52-27 52 0" fill="#4B64CF"/>
      <circle cx="86" cy="78" r="28" fill="#4B64CF"/>
      <text x="86" y="86" text-anchor="middle" fill="#FFF" font-size="22">03</text>
    </g>
    ${labels.map((label, i) => `<text x="${238 + i * 362}" y="492" text-anchor="middle" font-size="30" font-weight="600">${label}</text><text x="${238 + i * 362}" y="530" text-anchor="middle" font-size="21" fill="#586888">${notes[i]}</text>`).join("")}
    <path d="M238 565v22H962v-22M600 587v26" fill="none" stroke="#B3BDD4" stroke-width="2"/>
    <text x="600" y="644" text-anchor="middle" font-size="22" fill="#586888">${vi ? "Cùng tạo nên trải nghiệm người dùng" : "Together, shaping the user experience"}</text>
  </g>
</svg>`;
}

const copy = {
  vi: [
    "Ba con đường vào UX",
    "Người làm trải nghiệm người dùng thường đến từ nhiều lĩnh vực. Mỗi người mang theo một cách nhìn, và chính khác biệt ấy tạo nên thế mạnh.",
    "Khi những góc nhìn gặp nhau, một sản phẩm có thể vừa hữu ích, dễ hiểu, vừa gần với con người hơn.",
    "• Kỹ thuật biến ý tưởng thành những tương tác ổn định và có thể sử dụng được.",
    "• Thiết kế dùng chữ, hình ảnh và khoảng trống để dẫn dắt sự chú ý.",
    "• Nghiên cứu bắt đầu từ việc quan sát, lắng nghe và đặt đúng câu hỏi.",
    "Ba bước để bắt đầu",
    "1. Bắt đầu từ điều người đọc đang muốn hoàn thành.",
    "2. Lắng nghe một góc nhìn khác trước khi đưa ra lời giải.",
    "3. Ghi lại điều đã học bằng những câu ngắn và rõ.",
    "Chừa lại đủ khoảng trống cho một câu hỏi bạn chưa kịp nghĩ tới.",
    "Thiết kế tốt bắt đầu từ sự chú ý: tới con người, bối cảnh và những chi tiết nhỏ tạo nên khác biệt.",
    "Bạn có thể đọc theo nhịp của mình, hoặc nghe nội dung trong khi quan sát hình minh họa.",
    "Một góc nhìn mới",
    "Không gian để khám phá",
    "Cùng nhìn lại.",
    "Ba lĩnh vực không thay thế nhau. Chúng bổ sung cho nhau để câu chuyện trở nên trọn vẹn hơn.",
    "Hình 3.1. Kỹ thuật, thiết kế và nghiên cứu cùng tạo nên trải nghiệm người dùng.",
    "Mỗi góc nhìn giải quyết một phần khác nhau của cùng một vấn đề.",
    "Khi được đặt cạnh nhau, các quyết định trở nên rõ ràng và có căn cứ hơn.",
    "QUAN SÁT   LẮNG NGHE   KIỂM CHỨNG",
    "Giữ lại điều hữu ích, rồi tiếp tục câu chuyện.",
  ],
  en: [
    "Three paths into UX",
    "People come to user experience from many disciplines. Each brings a way of seeing the world, and that difference becomes a strength.",
    "When those perspectives meet, a product can be useful, clear and genuinely considerate of the people using it.",
    "• Engineering turns ideas into interactions that work reliably.",
    "• Design uses words, images and space to guide attention.",
    "• Research begins with observation, listening and better questions.",
    "Three ways to begin",
    "1. Start with what the reader is trying to accomplish.",
    "2. Listen to another perspective before proposing an answer.",
    "3. Write down what you learn in short, clear sentences.",
    "Leave enough room for a question you have not thought to ask yet.",
    "Good design begins with attention: to people, to context and to the small details that make a difference.",
    "Read at your own pace, or listen while you spend a moment with the illustration.",
    "A fresh perspective",
    "Room to explore",
    "Look again.",
    "The three disciplines do not replace one another. Together, they make the story more complete.",
    "Figure 3.1. Engineering, design and research shape the user experience together.",
    "Each perspective addresses a different part of the same problem.",
    "Placed side by side, they lead to decisions that are clearer and better grounded.",
    "OBSERVE   LISTEN   TEST",
    "Keep what is useful, then return to the story.",
  ],
} as const;

export function showcaseChapterCopy(locale: "vi" | "en"): readonly string[] {
  return copy[locale];
}
