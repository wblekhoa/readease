/** The ★ that puts a voice first (HIG 3.13), one button for the voice list
 * and the Voice picker so the two say and do the same thing: two shapes
 * for the two states - the outline, then that outline filled in the
 * favourite colour - and a bounce when the reader has just set it (HIG
 * 3.17). Never when a list opens with stars already on: the bounce answers
 * a press, and nothing was pressed. */
import { useState } from "react";
import { text } from "../i18n";
import { IconButton } from "./controls";
import { StarIcon, StarOutlineIcon } from "./icons";

export function FavoriteButton({
  name,
  on,
  onToggle,
}: {
  /** The voice's name as the row shows it: "Yêu thích {name}". */
  name: string;
  on: boolean;
  onToggle: () => void;
}) {
  const [pressed, setPressed] = useState(false);
  return (
    <IconButton
      onClick={() => {
        setPressed(true);
        onToggle();
      }}
      aria-pressed={on}
      aria-label={text("voices.favorite", { name })}
      title={text(on ? "voices.favorite_remove" : "voices.favorite_add")}
    >
      {/* The colour sits on the star itself: the button's own ink-mute
          would win a class-order contest on the button. */}
      {on ? <StarIcon className={`text-favorite ${pressed ? "star-pop" : ""}`} /> : <StarOutlineIcon />}
    </IconButton>
  );
}
