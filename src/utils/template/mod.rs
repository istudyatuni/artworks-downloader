use crate::{CrateError, Result};

mod parser;

#[derive(Debug, Default, PartialEq, Eq)]
pub struct Template {
    lexems: Vec<Lexem>,
}

impl TryFrom<&str> for Template {
    type Error = CrateError;

    fn try_from(value: &str) -> Result<Template> {
        let lexems = parser::parse_template(value)?;
        Ok(Self { lexems })
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Lexem {
    PathSep,
    Plain { text: String },
    Sub { name: String },
}

impl Lexem {
    fn sep() -> Self {
        Self::PathSep
    }
    fn sub<T: Into<String>>(n: T) -> Self {
        Self::Sub { name: n.into() }
    }
    fn plain<T: Into<String>>(t: T) -> Self {
        Self::Plain { text: t.into() }
    }
}
