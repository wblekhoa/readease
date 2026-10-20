// ReadEase icon B4·4: two 5-lobe wave strands on the brand squircle.
// usage: swiftc -O scripts/render-icon.swift -o /tmp/render-icon && /tmp/render-icon <out.png> <pixels> <mode>
//   icon        → assets/branding/readease-icon-master.png (1024; macOS grid, 824 body), then
//                 ./scripts/build-icon.sh and `tauri icon` for the bundle sets
//   mark        → app/src/assets/readease-mark.png (128) and site/icon.png (256), full bleed
//   glyph-white → assets/branding/readease-wave-mark-flat-white.png (64), white strands only
// Vector twin: assets/branding/readease-icon.svg (same formula).
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
let out = URL(fileURLWithPath: args[1]), px = CGFloat(Double(args[2])!), mode = args[3]
let brand = CGColor(srgbRed: 0x2B/255, green: 0x52/255, blue: 0xD4/255, alpha: 1)
let back = CGColor(srgbRed: 0xA7/255, green: 0xB7/255, blue: 0xED/255, alpha: 1)
let white = CGColor(srgbRed: 1, green: 1, blue: 1, alpha: 1)

// Design units: a 92-unit body (4..96) on a 100 grid. macOS icon grid: the
// body is 824/1024 of the canvas; a mark/glyph fills the canvas.
let body: CGFloat = mode == "icon" ? px * 824 / 1024 : px
let origin: CGFloat = (px - body) / 2
let unit = body / 92
func p(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: origin + (x - 4) * unit, y: origin + (y - 4) * unit) }

func strand(_ phase: CGFloat) -> CGPath {
    let path = CGMutablePath()
    let steps = 720
    for i in 0..<steps {
        let t = 2 * CGFloat.pi * CGFloat(i) / CGFloat(steps) - .pi / 2
        let r = 25 + 5.5 * sin(5 * t + phase)
        let point = p(50 + r * cos(t), 50 + r * sin(t))
        if i == 0 { path.move(to: point) } else { path.addLine(to: point) }
    }
    path.closeSubpath()
    return path
}

let ctx = CGContext(data: nil, width: Int(px), height: Int(px), bitsPerComponent: 8, bytesPerRow: 0,
                    space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
ctx.setShouldAntialias(true)
ctx.interpolationQuality = .high
// Flip so design y grows downward like the SVG.
ctx.translateBy(x: 0, y: px); ctx.scaleBy(x: 1, y: -1)
if mode != "glyph-white" {
    let rect = CGRect(x: origin, y: origin, width: body, height: body)
    ctx.addPath(CGPath(roundedRect: rect, cornerWidth: body * 0.225, cornerHeight: body * 0.225, transform: nil))
    ctx.setFillColor(brand); ctx.fillPath()
}
// Each strand as a filled outline (nonzero), so no seam can open where the
// sampled curve's segments meet.
func band(_ phase: CGFloat) -> CGPath {
    strand(phase).copy(strokingWithWidth: 5.5 * unit, lineCap: .round, lineJoin: .round, miterLimit: 10)
}
ctx.addPath(band(.pi)); ctx.setFillColor(mode == "glyph-white" ? white.copy(alpha: 0.55)! : back); ctx.fillPath(using: .winding)
ctx.addPath(band(0)); ctx.setFillColor(white); ctx.fillPath(using: .winding)
let image = ctx.makeImage()!
let dest = CGImageDestinationCreateWithURL(out as CFURL, UTType.png.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(dest, image, nil); CGImageDestinationFinalize(dest)
print("wrote", out.path, Int(px))
