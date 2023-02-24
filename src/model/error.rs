pub type Result<T, E = CrateError> = std::result::Result<T, E>;

#[derive(thiserror::Error, Debug)]
pub enum CrateError {
    #[error("string template parse error: {0}")]
    FarError(#[from] far::Errors),
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

    #[error("error: {0}")]
    /// Variant for all other errors
    Plain(String),
}

impl CrateError {
    pub fn missing_template_key<T: Into<String>>(key: T) -> Self {
        Self::MissingTemplateKey(key.into())
    }
    pub fn plain<T: Into<String>>(msg: T) -> Self {
        Self::Plain(msg.into())
    }
}
