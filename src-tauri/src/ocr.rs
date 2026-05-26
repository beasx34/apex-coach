//! OCR backends. The default backend on Windows is `Windows.Media.Ocr` which
//! ships with Windows 10+ and requires no extra install. On other platforms
//! (CI on Linux, dev machines) we fall back to a no-op that returns an empty
//! string, so the Rust crate still compiles and unit-testable code paths work.

use anyhow::Result;
use async_trait::async_trait;

use crate::capture::Frame;

#[async_trait]
pub trait OcrBackend: Send + Sync {
    async fn recognize(&self, frame: &Frame) -> Result<String>;
    fn name(&self) -> &'static str;
}

/// Construct the best available backend for the current host.
pub fn make_backend() -> Result<Box<dyn OcrBackend>> {
    #[cfg(windows)]
    {
        match windows_backend::WindowsOcr::new() {
            Ok(b) => return Ok(Box::new(b)),
            Err(e) => tracing::warn!(?e, "Windows.Media.Ocr unavailable; falling back to noop"),
        }
    }
    Ok(Box::new(NoopOcr))
}

/// Fallback used in CI and on non-Windows hosts.
pub struct NoopOcr;

#[async_trait]
impl OcrBackend for NoopOcr {
    async fn recognize(&self, _frame: &Frame) -> Result<String> {
        Ok(String::new())
    }
    fn name(&self) -> &'static str {
        "noop"
    }
}

#[cfg(windows)]
pub mod windows_backend {
    use super::*;
    use anyhow::{anyhow, Context};
    use windows::core::Interface;
    use windows::Globalization::Language;
    use windows::Graphics::Imaging::{BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap};
    use windows::Media::Ocr::OcrEngine;
    use windows::Storage::Streams::{Buffer, IBuffer};

    pub struct WindowsOcr {
        engine: OcrEngine,
    }

    impl WindowsOcr {
        pub fn new() -> Result<Self> {
            // Prefer the user profile languages; if that fails (no language pack),
            // fall back to a forced en-US engine, which is sufficient for digit OCR.
            let engine = match OcrEngine::TryCreateFromUserProfileLanguages() {
                Ok(e) => e,
                Err(_) => {
                    let lang = Language::CreateLanguage(&"en-US".into())
                        .context("create Language en-US")?;
                    OcrEngine::TryCreateFromLanguage(&lang).context("create OcrEngine en-US")?
                }
            };
            Ok(Self { engine })
        }

        fn frame_to_bitmap(frame: &Frame) -> Result<SoftwareBitmap> {
            if frame.rgba.is_empty() || frame.width == 0 || frame.height == 0 {
                return Err(anyhow!("empty frame"));
            }
            // Build a SoftwareBitmap with BGRA8 pixel format from our RGBA bytes.
            let buf = Buffer::Create(frame.rgba.len() as u32).context("Buffer::Create")?;
            buf.SetLength(frame.rgba.len() as u32)
                .context("SetLength")?;
            let ibuf: IBuffer = buf.cast().context("cast IBuffer")?;
            unsafe {
                let bba: windows::Win32::System::WinRT::IBufferByteAccess = ibuf.cast()?;
                let ptr = bba.Buffer().context("IBufferByteAccess::Buffer")?;
                if ptr.is_null() {
                    return Err(anyhow!("null buffer pointer"));
                }
                let dst = std::slice::from_raw_parts_mut(ptr, frame.rgba.len());
                // Swap R <-> B because SoftwareBitmap is BGRA.
                for (i, chunk) in frame.rgba.chunks_exact(4).enumerate() {
                    let off = i * 4;
                    dst[off] = chunk[2];
                    dst[off + 1] = chunk[1];
                    dst[off + 2] = chunk[0];
                    dst[off + 3] = chunk[3];
                }
            }
            let bmp = SoftwareBitmap::CreateCopyFromBuffer(
                &ibuf,
                BitmapPixelFormat::Bgra8,
                frame.width as i32,
                frame.height as i32,
            )
            .context("CreateCopyFromBuffer")?;
            // Ensure premultiplied alpha because Bgra8 default is premultiplied.
            let conv = SoftwareBitmap::ConvertWithAlpha(
                &bmp,
                BitmapPixelFormat::Bgra8,
                BitmapAlphaMode::Premultiplied,
            )
            .context("ConvertWithAlpha")?;
            Ok(conv)
        }
    }

    #[async_trait::async_trait]
    impl OcrBackend for WindowsOcr {
        async fn recognize(&self, frame: &Frame) -> Result<String> {
            let bmp = Self::frame_to_bitmap(frame)?;
            let op = self
                .engine
                .RecognizeAsync(&bmp)
                .context("OcrEngine::RecognizeAsync")?;
            let result = op.get().context("await OCR result")?;
            let text = result.Text().context("OCR text")?;
            Ok(text.to_string())
        }

        fn name(&self) -> &'static str {
            "windows-media-ocr"
        }
    }
}
