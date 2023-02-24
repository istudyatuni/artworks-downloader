use std::{collections::HashMap, hash::Hash, path::PathBuf, str::FromStr};

use crate::{CrateError, Result};

mod parser;

#[derive(Debug, Default, PartialEq, Eq)]
pub struct Template {
    lexems: Vec<Lexem>,
}

impl Template {
    pub fn render_map<V>(&self, map: HashMap<String, V>) -> Result<PathBuf>
    where
        V: ToString,
    {
        let mut path = PathBuf::new();
        let mut segment = String::new();
        for l in &self.lexems {
            match l {
                Lexem::PathSep => {
                    path.push(segment.clone());
                    segment.clear();
                }
                Lexem::Plain { text } => segment.push_str(text),
                Lexem::Sub { name } => {
                    let Some(value) = map.get(name) else {
                        return Err(CrateError::missing_template_key(name))
                    };
                    segment.push_str(&value.to_string())
                }
            }
        }
        Ok(path)
    }
    pub fn render<K, V, I>(&self, it: I) -> Result<PathBuf>
    where
        K: Eq + ToString,
        V: ToString,
        I: IntoIterator<Item = (K, V)>,
    {
        let mut map = HashMap::new();
        for (k, v) in it {
            map.insert(k.to_string(), v);
        }
        self.render_map(map)
    }
}

impl TryFrom<&str> for Template {
    type Error = CrateError;

    fn try_from(value: &str) -> Result<Template> {
        let lexems = parser::parse_path_template(value)?;
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
