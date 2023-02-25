use std::collections::HashMap;

use crate::{CrateError, Result};

mod parser;

#[derive(Debug, Default, PartialEq, Eq)]
pub struct Template {
    lexems: Vec<Lexem>,
}

impl Template {
    fn render_map<V: ToString>(&self, map: HashMap<String, V>) -> Result<String> {
        let mut result = String::new();
        for l in &self.lexems {
            match l {
                Lexem::Plain { text } => result.push_str(text),
                Lexem::Sub { name } => {
                    let Some(value) = map.get(name) else {
                        return Err(CrateError::missing_template_key(name))
                    };
                    result.push_str(&value.to_string())
                }
            }
        }
        Ok(result)
    }
    pub fn render<K, V, I>(&self, it: I) -> Result<String>
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
        let lexems = parser::parse_template(value)?;
        Ok(Self { lexems })
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
enum Lexem {
    Plain { text: String },
    Sub { name: String },
}

impl Lexem {
    fn sub<T: Into<String>>(n: T) -> Self {
        Self::Sub { name: n.into() }
    }
    fn plain<T: Into<String>>(t: T) -> Self {
        Self::Plain { text: t.into() }
    }
}

#[cfg(test)]
mod test {
    use super::{Lexem, Template};

    #[test]
    fn render_test() {
        let lexems = vec![Lexem::plain("text-"), Lexem::sub("test")];
        let t = Template { lexems };
        let sub = [("test", "asdf")];
        assert_eq!(t.render(sub).unwrap(), String::from("text-asdf"));
    }
}
