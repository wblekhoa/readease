fn main() {
    // The Objective-C selection bridge compiles straight into the binary:
    // no dylib to locate at runtime, nothing extra to bundle in milestone D.
    // Same source file the Qt app ships - the ABI is the contract.
    let manifest = std::env::var("CARGO_MANIFEST_DIR").expect("manifest dir");
    let source = std::path::PathBuf::from(&manifest)
        .join("../../native/macos/ReadEaseSelectionNative.m");
    let out_dir = std::path::PathBuf::from(std::env::var("OUT_DIR").expect("out dir"));
    let object = out_dir.join("selection_native.o");
    let status = std::process::Command::new("xcrun")
        .args([
            "--sdk", "macosx", "clang", "-c",
            "-fobjc-arc", "-fmodules",
            "-mmacosx-version-min=15.0", "-O2",
        ])
        .arg(&source)
        .arg("-o")
        .arg(&object)
        .status()
        .expect("run clang for the selection bridge");
    assert!(status.success(), "selection bridge failed to compile");
    println!("cargo:rustc-link-arg={}", object.display());
    println!("cargo:rustc-link-lib=framework=Cocoa");
    println!("cargo:rustc-link-lib=framework=ApplicationServices");
    println!("cargo:rustc-link-lib=framework=Carbon");
    println!("cargo:rerun-if-changed={}", source.display());
    tauri_build::build()
}
