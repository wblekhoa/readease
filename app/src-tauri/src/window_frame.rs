//! The window must open inside a screen, at a size that leaves the screen's
//! edges visible.
//!
//! The window-state plugin brings back the last size and position, but it
//! stores and restores them in physical pixels. With screens of different
//! scales (a 2x Retina panel next to a 1x monitor) a frame saved on one and
//! restored on the other comes back twice as big; the next save keeps the
//! doubled size, so the window grew on every launch until it was wider than
//! any screen (owner 04/11/2026: a saved frame of 6912 x 1996 px).
//!
//! So the main window skips the plugin's restore and `restore_window` puts
//! the saved frame back in logical points, through `fit`. `fit` works in logical
//! points, the one space every macOS screen shares, picks the screen that
//! holds most of the window, and answers:
//! - nothing, when the frame sits inside that screen with room at the edges;
//! - the same size moved inside, when the frame fits but hangs off an edge;
//! - the default size (capped to 90% of the screen) centred, when the frame
//!   is as big as the screen or bigger - a restored size that large is the
//!   bug above, not a choice.

/// A rectangle in logical points.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Rect {
    pub x: f64,
    pub y: f64,
    pub w: f64,
    pub h: f64,
}

/// Room kept between the window and each edge of the screen's work area.
/// A frame closer than this to both sides of an axis counts as "screen-sized".
const EDGE: f64 = 16.0;
/// The share of the work area a reset window may take at most.
const MAX_SHARE: f64 = 0.9;

fn overlap(a: &Rect, b: &Rect) -> f64 {
    let w = (a.x + a.w).min(b.x + b.w) - a.x.max(b.x);
    let h = (a.y + a.h).min(b.y + b.h) - a.y.max(b.y);
    if w > 0.0 && h > 0.0 { w * h } else { 0.0 }
}

/// The frame the window should take, or `None` when it is fine as it is.
/// `screens` are the work areas (menu bar and Dock left out); `primary` is
/// the index used when the window touches none of them.
pub fn fit(frame: Rect, screens: &[Rect], primary: usize, default: (f64, f64), min: (f64, f64)) -> Option<Rect> {
    let screen = screens
        .iter()
        .map(|s| (overlap(&frame, s), s))
        .filter(|(area, _)| *area > 0.0)
        .max_by(|a, b| a.0.total_cmp(&b.0))
        .map(|(_, s)| *s)
        .or_else(|| screens.get(primary).copied())?;

    let too_big = frame.w > screen.w - 2.0 * EDGE || frame.h > screen.h - 2.0 * EDGE;
    if too_big {
        let w = default.0.min(screen.w * MAX_SHARE).max(min.0.min(screen.w));
        let h = default.1.min(screen.h * MAX_SHARE).max(min.1.min(screen.h));
        return Some(Rect {
            x: (screen.x + (screen.w - w) / 2.0).round(),
            y: (screen.y + (screen.h - h) / 2.0).round(),
            w,
            h,
        });
    }

    let x = frame.x.clamp(screen.x, screen.x + screen.w - frame.w);
    let y = frame.y.clamp(screen.y, screen.y + screen.h - frame.h);
    if x == frame.x && y == frame.y {
        None
    } else {
        Some(Rect { x, y, ..frame })
    }
}

/// A screen as the window sees it: its whole rectangle in physical pixels
/// (the space the plugin saved the frame in), its scale, and its work area
/// in logical points.
#[derive(Clone, Copy, Debug)]
pub struct Screen {
    pub physical: Rect,
    pub scale: f64,
    pub work: Rect,
}

/// The frame to open at, in logical points, from the plugin's saved one
/// (physical pixels: `outer_position` and `inner_size` times the scale of the
/// screen the window was on). `None`: nothing saved, keep the config's size.
pub fn restored(saved: Option<Rect>, screens: &[Screen], primary: usize, default: (f64, f64), min: (f64, f64)) -> Option<Rect> {
    let saved = saved?;
    let scale = screens
        .iter()
        .find(|s| {
            let p = s.physical;
            saved.x >= p.x && saved.x < p.x + p.w && saved.y >= p.y && saved.y < p.y + p.h
        })
        .map_or(1.0, |s| s.scale);
    let frame = Rect { x: saved.x / scale, y: saved.y / scale, w: saved.w / scale, h: saved.h / scale };
    let work: Vec<Rect> = screens.iter().map(|s| s.work).collect();
    Some(fit(frame, &work, primary, default, min).unwrap_or(frame))
}

/// The plugin's saved frame for `label`, in physical pixels.
fn saved_frame<R: tauri::Runtime>(window: &tauri::Window<R>, label: &str) -> Option<Rect> {
    use tauri::Manager;
    let path = window.app_handle().path().app_config_dir().ok()?.join(".window-state.json");
    let all: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(path).ok()?).ok()?;
    let main = all.get(label)?;
    let n = |key: &str| main.get(key).and_then(serde_json::Value::as_f64);
    let (w, h) = (n("width")?, n("height")?);
    (w > 0.0 && h > 0.0).then(|| Some(Rect { x: n("x")?, y: n("y")?, w, h })).flatten()
}

/// Opens the main window at its saved frame, kept on a screen and smaller
/// than one. Replaces the plugin's own restore for this window (which sets
/// the saved physical size at whatever scale the new window starts on).
pub fn restore_window<R: tauri::Runtime>(window: &tauri::Window<R>, default: (f64, f64), min: (f64, f64)) {
    let monitors = window.available_monitors().unwrap_or_default();
    let primary = window.primary_monitor().ok().flatten();
    let screens: Vec<Screen> = monitors
        .iter()
        .map(|m| {
            let s = m.scale_factor();
            let (p, z, area) = (m.position(), m.size(), m.work_area());
            Screen {
                physical: Rect { x: p.x as f64, y: p.y as f64, w: z.width as f64, h: z.height as f64 },
                scale: s,
                work: Rect {
                    x: area.position.x as f64 / s,
                    y: area.position.y as f64 / s,
                    w: area.size.width as f64 / s,
                    h: area.size.height as f64 / s,
                },
            }
        })
        .collect();
    let primary_index = primary
        .and_then(|p| monitors.iter().position(|m| m.position() == p.position()))
        .unwrap_or(0);
    let saved = saved_frame(window, window.label());
    if let Some(to) = restored(saved, &screens, primary_index, default, min) {
        eprintln!("window: saved {saved:?} opens at {to:?}");
        let _ = window.set_size(tauri::LogicalSize::new(to.w, to.h));
        let _ = window.set_position(tauri::LogicalPosition::new(to.x, to.y));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const DEFAULT: (f64, f64) = (1280.0, 820.0);
    const MIN: (f64, f64) = (960.0, 600.0);

    // The owner's desk on 04/11/2026: a 2560x1440 monitor (main, 1x), the
    // MacBook's 1728x1117 panel to its left, a 1920x1080 monitor. Work areas
    // leave out the menu bar (and the Dock on the main screen).
    fn desk() -> Vec<Rect> {
        vec![
            Rect { x: 0.0, y: 25.0, w: 2560.0, h: 1340.0 },
            Rect { x: -1728.0, y: 719.0 + 33.0, w: 1728.0, h: 1084.0 },
            Rect { x: 2560.0, y: 0.0 + 25.0, w: 1920.0, h: 1055.0 },
        ]
    }

    #[test]
    fn a_doubled_frame_comes_back_at_the_default_size_centred() {
        // The saved frame: 6912 x 1996 px at (-3456, 1438) on the 2x panel.
        let frame = Rect { x: -1728.0, y: 719.0, w: 3456.0, h: 998.0 };
        let to = fit(frame, &desk(), 0, DEFAULT, MIN).expect("must be fixed");
        assert_eq!((to.w, to.h), (1280.0, 820.0));
        let s = desk()[1];
        assert_eq!(to.x, (s.x + (s.w - 1280.0) / 2.0).round());
        assert_eq!(to.y, (s.y + (s.h - 820.0) / 2.0).round());
    }

    #[test]
    fn a_frame_as_wide_as_the_screen_is_reset() {
        // What the owner saw: the window from edge to edge of the MacBook.
        let frame = Rect { x: -1728.0, y: 752.0, w: 1728.0, h: 1000.0 };
        let to = fit(frame, &desk(), 0, DEFAULT, MIN).expect("must be fixed");
        assert_eq!((to.w, to.h), (1280.0, 820.0));
        assert!(to.x > -1728.0 && to.x + to.w < 0.0);
    }

    #[test]
    fn a_frame_that_fits_stays() {
        let frame = Rect { x: 400.0, y: 200.0, w: 1280.0, h: 820.0 };
        assert_eq!(fit(frame, &desk(), 0, DEFAULT, MIN), None);
    }

    #[test]
    fn a_frame_hanging_off_an_edge_moves_inside_at_its_size() {
        let frame = Rect { x: 2000.0, y: 900.0, w: 1100.0, h: 700.0 };
        // Mostly on the main screen: pulled back so its right edge is on it.
        let to = fit(frame, &desk(), 0, DEFAULT, MIN).expect("must move");
        assert_eq!((to.w, to.h), (1100.0, 700.0));
        assert_eq!(to.x, 2560.0 - 1100.0);
        assert_eq!(to.y, 25.0 + 1340.0 - 700.0);
    }

    #[test]
    fn a_frame_on_no_screen_goes_to_the_primary_one() {
        let frame = Rect { x: 9000.0, y: 9000.0, w: 1000.0, h: 700.0 };
        let to = fit(frame, &desk(), 0, DEFAULT, MIN).expect("must move");
        assert!(to.x >= 0.0 && to.x + to.w <= 2560.0);
    }

    #[test]
    fn on_a_small_screen_the_reset_takes_90_percent_but_not_below_the_minimum() {
        let small = vec![Rect { x: 0.0, y: 25.0, w: 1280.0, h: 775.0 }];
        let frame = Rect { x: 0.0, y: 25.0, w: 1280.0, h: 820.0 };
        let to = fit(frame, &small, 0, DEFAULT, MIN).expect("must be fixed");
        assert_eq!(to.w, 1152.0);
        assert_eq!(to.h, 697.5);
    }

    fn desk_screens() -> Vec<Screen> {
        let d = desk();
        vec![
            Screen { physical: Rect { x: 0.0, y: 0.0, w: 2560.0, h: 1440.0 }, scale: 1.0, work: d[0] },
            Screen { physical: Rect { x: -3456.0, y: 1438.0, w: 3456.0, h: 2234.0 }, scale: 2.0, work: d[1] },
            Screen { physical: Rect { x: 2560.0, y: 0.0, w: 1920.0, h: 1080.0 }, scale: 1.0, work: d[2] },
        ]
    }

    #[test]
    fn the_owners_saved_frame_opens_at_the_default_size_on_the_macbook() {
        let saved = Rect { x: -3456.0, y: 1438.0, w: 6912.0, h: 1996.0 };
        let to = restored(Some(saved), &desk_screens(), 0, DEFAULT, MIN).unwrap();
        assert_eq!((to.w, to.h), (1280.0, 820.0));
        assert!(to.x >= -1728.0 && to.x + to.w <= 0.0, "{to:?}");
    }

    #[test]
    fn a_saved_frame_on_the_2x_panel_comes_back_at_half_its_pixels() {
        let saved = Rect { x: -3200.0, y: 1600.0, w: 2400.0, h: 1600.0 };
        let to = restored(Some(saved), &desk_screens(), 0, DEFAULT, MIN).unwrap();
        assert_eq!(to, Rect { x: -1600.0, y: 800.0, w: 1200.0, h: 800.0 });
    }

    #[test]
    fn nothing_saved_keeps_the_config_size() {
        assert_eq!(restored(None, &desk_screens(), 0, DEFAULT, MIN), None);
    }
}
