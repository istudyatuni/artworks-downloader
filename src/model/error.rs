pub type Result<T, E = CrateError> = std::result::Result<T, E>;

#[derive(thiserror::Error, Debug)]
pub enum CrateError {
    #[error("string template parse error: {0}")]
    FarError(#[from] far::Errors),
}
