pub type Result<T, E = CrateError> = std::result::Result<T, E>;

#[derive(thiserror::Error, Debug)]
pub enum CrateError {
    #[error("io error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("reqwest error: {0}")]
    ReqwestError(#[from] reqwest::Error),

    #[error("invalid url: {0}")]
    InvalidURL(String),
    #[error("unsupported url: {0}")]
    UnsupportedURL(String),

    #[error("invalid pattern: {0}")]
    InvalidPattern(String),
    #[error("missing key for template: {0}")]
    MissingTemplateKey(String),

    #[error("skip existing: {0}")]
    SkipExisting(String),

    #[error("error: {0}")]
    /// Variant for all other errors
    Plain(String),
}

impl CrateError {
    pub fn invalid_url<T: Into<String>>(url: T) -> Self {
        Self::InvalidURL(url.into())
    }
    pub fn unsupported_url<T: Into<String>>(url: T) -> Self {
        Self::UnsupportedURL(url.into())
    }
    pub fn missing_template_key<T: Into<String>>(key: T) -> Self {
        Self::MissingTemplateKey(key.into())
    }
    pub fn skip_existing<T: Into<String>>(url: T) -> Self {
        Self::SkipExisting(url.into())
    }
    pub fn plain<T: Into<String>>(msg: T) -> Self {
        Self::Plain(msg.into())
    }
}
