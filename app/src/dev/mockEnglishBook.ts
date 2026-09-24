/** An English document for the preview harness: the shelf's fourth book,
 * the one the Vietnamese voice refuses. It used to open as the Vietnamese
 * sample, so nothing English could be looked at in the reader - not its
 * text, not its contents, not its pictures.
 *
 * Invented text, like every fixture here. It carries every kind of block
 * the Vietnamese sample does (heading, paragraph, a paragraph cut for the
 * voice, lists typed and numbered by structure, quotations and label-like
 * quotes, captions) and the same drawings with their words in English
 * (`en-` ids in mockFigures.ts), each in its own shape. Imported only by the
 * DEV mock host, so none of it reaches a build.
 */

type Block = { text: string; kind?: string; joint?: string; marker?: string };
type Picture = {
  id: string;
  /** The block (index after the chapter's heading) it hangs on. */
  at: number;
  placement?: "before" | "after";
  alt: string;
  label?: string;
  /** The block that captions it, when the book gave it one. */
  caption?: number;
};

const CHAPTERS: Array<{ title: string; blocks: Block[]; pictures?: Picture[] }> = [
  {
    title: "Before you begin",
    blocks: [
      { text: "This guide is for small teams that make software people use every day. It is not a theory of design; it is a set of habits that held up across many projects, written down so that someone new can pick them up in a week rather than a year." },
      { text: "Each chapter stands on its own. Read them in order the first time, then open the one you need. The exercises at the end of each part take an afternoon, and they are worth more than the chapters around them." },
      { text: "Where a number appears, it is there to show a shape, not to be quoted. Your product has its own numbers, and finding them is part of the work." },
    ],
  },
  {
    title: "Start with the problem",
    blocks: [
      { text: "Most teams are good at building what they were asked for. Fewer are good at asking whether it was the right thing to build. The difference rarely shows in the first release; it shows a year later, in the features nobody opens." },
      { text: "Before you draw a single screen, write the problem down in one sentence, in the words of the person who has it. If you cannot, you do not understand it yet, and no amount of polish will make up for that." },
      { text: "A product has to work before it can be anything else. But working is only the ground floor: people forgive a lot in a tool that is reliable and easy to use, and they come back to one that is also a pleasure to use." },
      { text: "Figure 1.1. The hierarchy of experience: functional, reliable, usable, memorable.", kind: "caption" },
      { text: "The way people tell computers what to do has changed several times within one working life. Each change felt like a novelty at first and then, very quickly, like the obvious way things had always been." },
      { text: "The lesson is not to chase the newest input. It is to notice what each one made easy, and what it quietly made hard." },
    ],
    pictures: [
      { id: "en-fig-wide", at: 2, alt: "The hierarchy of experience: functional, reliable, usable, memorable", label: "Figure 1.1", caption: 3 },
      { id: "en-fig-timeline", at: 4, alt: "From mouse and windows (1984) to chatting with AI (2022)", label: "Figure 1.2" },
    ],
  },
  {
    title: "Three paths into UX",
    blocks: [
      { text: "Most people who design software did not start there. They came from a neighbouring craft and brought its way of seeing with them, and that way of seeing is where their strength comes from." },
      { text: "This is the rest of the same paragraph, cut in two for the voice: on the page it runs on from the sentence before instead of opening a new paragraph.", joint: "split" },
      { text: "• Web and software development. A natural route, because you already know what is hard to build.", kind: "list_item" },
      { text: "• Graphic and print design. Every decision about type and space is a decision about attention.", kind: "list_item" },
      { text: "• Research, sociology and psychology. You know how to ask a question without leading the answer.", kind: "list_item" },
      { text: "Three ways to begin", kind: "heading" },
      { text: "1. Start upstream, where the ideas come from.", kind: "list_item" },
      { text: "2. Find the one person who could sink your project, and talk to them first.", kind: "list_item" },
      { text: "3. Write down what you learned. Keep it short.", kind: "list_item" },
      { text: "Good design is a way of paying attention to other people.", kind: "quote" },
      { text: "Right below are short quotations used as labels: three words or fewer and no closing mark. The third is just as short but ends with a full stop, so it stays a quotation." },
      { text: "Short label", kind: "quote" },
      { text: "No full stop", kind: "quote" },
      { text: "Keep it short.", kind: "quote" },
      { text: "Ordinary text again, to compare the spacing. Below is a figure with the book's own label: its caption introduces it, so the voice does not say “See figure” first." },
      { text: "Figure 2.1. Three paths into UX, redrawn from the original.", kind: "caption" },
      { text: "A list numbered by its structure: the text of each item carries no number; the number is built when the document opens." },
      { text: "Write your question down before you read.", kind: "list_item", marker: "1." },
      { text: "Skim once to see the frame.", kind: "list_item", marker: "2." },
      { text: "Go back to the hard parts and read them slowly.", kind: "list_item", marker: "3." },
    ],
    pictures: [
      { id: "en-fig-venn", at: 14, alt: "Figure 2.1. Three paths into UX, redrawn from the original.", label: "Figure 2.1", caption: 15 },
    ],
  },
  {
    title: "Talk to people",
    blocks: [
      { text: "Before the interview", kind: "heading" },
      { text: "An interview is not a survey read aloud. You are there to hear the story of the last time something happened, in as much detail as the person can remember." },
      { text: "Write five questions, then cross out the two that ask people to predict their own behaviour. Nobody knows what they would do; everybody knows what they did." },
      { text: "During the interview", kind: "heading" },
      { text: "Ask about the last time, not the usual time.", kind: "list_item", marker: "1." },
      { text: "Let silence do some of the work.", kind: "list_item", marker: "2." },
      { text: "Write down their words, not your summary of them.", kind: "list_item", marker: "3." },
      { text: "Afterwards, spread the notes out and group them before anyone is allowed an opinion. The pattern you find on the wall is more honest than the one you walked in with." },
    ],
    pictures: [
      { id: "en-fig-scene", at: 2, alt: "A user interview: two people at a table, a wall of sticky notes behind them", label: "Figure 3.1" },
    ],
  },
  {
    title: "Sketch before you build",
    blocks: [
      { text: "A sketch is a question you can hold. It costs five minutes, it invites criticism, and nobody is attached to it yet, which is exactly why it is worth making." },
      { text: "Draw the page three different ways before you choose one. The first idea is usually the one everybody else already had." },
      { text: "Keep the sketches. When a decision is questioned later, the versions you threw away explain it better than any document." },
    ],
    // No label of the book's own and no background of its own, like the
    // Vietnamese book's sketch.
    pictures: [
      { id: "en-fig-lineart", at: 0, alt: "A hand-drawn wireframe of a homepage, with notes in red pen" },
    ],
  },
  {
    title: "States, not screens",
    blocks: [
      { text: "A screen is a snapshot; a product is everything in between. Every control you design has at least four lives: at rest, under the pointer, busy, and unavailable." },
      { text: "Draw them together, side by side, so that the differences are deliberate rather than accidental." },
      { text: "The busy state is the one teams forget. A button that shows nothing for two seconds gets pressed a second time." },
    ],
    pictures: [
      { id: "en-fig-small", at: 1, alt: "Three states of a button: default, hover, saving", label: "Figure 5.1" },
    ],
  },
  {
    title: "Measure what matters",
    blocks: [
      { text: "Measure the moments where people give up, not only the moments where they succeed. A sign-up flow that loses a third of its visitors at one step is telling you exactly where to look." },
      { text: "In the example, most of the loss happens at email verification, between one screen and the next. The fix was not a better screen; it was letting people start before they had verified." },
      { text: "A number with no decision attached to it is decoration. Before you add a metric, write down what you would do if it doubled, and what you would do if it halved." },
    ],
    pictures: [
      { id: "en-fig-chart", at: 0, alt: "The share of people still with us after each sign-up step", label: "Figure 6.1" },
    ],
  },
  {
    title: "Ship, then listen",
    blocks: [
      { text: "The first version is where the real research begins. Put it in front of people early, watch what they do in the first ten minutes, and change the welcome screen before you change anything else." },
      { text: "Onboarding is a promise. If it says the app will remind you at the right time, the reminder had better arrive, and it had better be easy to turn off." },
      { text: "Then keep listening for longer than feels comfortable. The complaints that repeat are the roadmap." },
    ],
    // Before the first paragraph, with the alt text books so often ship.
    pictures: [
      { id: "en-fig-tall", at: 0, placement: "before", alt: "Image" },
    ],
  },
  {
    title: "Acknowledgements",
    blocks: [
      { text: "This guide grew out of many projects and many patient colleagues. The mistakes in it are ours; the good habits were borrowed from people who had already made those mistakes." },
    ],
  },
];

const segmentId = (chapter: number, block: number) => `en-ch-${chapter}-seg-${block}`;

/** The book as `book.open` answers it: every chapter opens with its title
 * as a heading, then its blocks. */
export const ENGLISH_BOOK = {
  id: "book-four",
  title: "The Design Team's Field Guide",
  chapters: CHAPTERS.map(({ title, blocks, pictures = [] }, chapter) => ({
    id: `en-ch-${chapter}`,
    title,
    figures: pictures.map((picture, index) => ({
      id: picture.id,
      anchor_segment_id: segmentId(chapter, picture.at),
      placement: picture.placement ?? "after",
      alt: picture.alt,
      number: index + 1,
      alt_is_generic: picture.alt === "Image",
      ...(picture.label ? { label: picture.label } : {}),
      ...(picture.caption !== undefined ? { caption_segment_id: segmentId(chapter, picture.caption) } : {}),
    })),
    segments: [
      { id: `en-ch-${chapter}-seg-h`, text: title, kind: "heading", joint: "block" },
      ...blocks.map((block, index) => ({
        id: segmentId(chapter, index),
        text: block.text,
        kind: block.kind ?? "paragraph",
        joint: block.joint ?? "block",
        ...(block.marker ? { marker: block.marker } : {}),
      })),
    ],
  })),
};

/** Its contents as a publisher writes them (HIG 3.25): front matter, two
 * parts of numbered chapters, sections under three of them, back matter. */
export const ENGLISH_TOC: Array<{ level: number; title: string; segment_id: string }> = [
  { level: 1, title: "Before you begin", segment_id: "en-ch-0-seg-h" },
  { level: 1, title: "Part One: Foundations", segment_id: "en-ch-1-seg-h" },
  { level: 2, title: "Chapter 1 Start with the problem", segment_id: "en-ch-1-seg-h" },
  { level: 2, title: "Chapter 2 Three paths into UX", segment_id: "en-ch-2-seg-h" },
  { level: 3, title: "Where designers come from", segment_id: "en-ch-2-seg-0" },
  { level: 3, title: "Three ways to begin", segment_id: "en-ch-2-seg-5" },
  { level: 1, title: "Part Two: Practice", segment_id: "en-ch-3-seg-h" },
  { level: 2, title: "Chapter 3 Talk to people", segment_id: "en-ch-3-seg-h" },
  { level: 3, title: "Before the interview", segment_id: "en-ch-3-seg-0" },
  { level: 3, title: "During the interview", segment_id: "en-ch-3-seg-3" },
  { level: 2, title: "Chapter 4 Sketch before you build", segment_id: "en-ch-4-seg-h" },
  { level: 2, title: "Chapter 5 States, not screens", segment_id: "en-ch-5-seg-h" },
  { level: 2, title: "Chapter 6 Measure what matters", segment_id: "en-ch-6-seg-h" },
  { level: 2, title: "Chapter 7 Ship, then listen", segment_id: "en-ch-7-seg-h" },
  { level: 1, title: "Acknowledgements", segment_id: "en-ch-8-seg-h" },
];
