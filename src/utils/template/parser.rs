use nom::{
    branch::alt,
    bytes::complete::{tag, take_till, take_while},
    combinator::eof,
    multi::many_till,
    sequence::delimited,
    IResult,
};

use super::Lexem;
use crate::{CrateError, Result};

fn sub(i: &str) -> IResult<&str, Lexem> {
    let is_key = |c: char| c.is_alphabetic() || c == '_';
    delimited(tag("{"), take_while(is_key), tag("}"))(i).map(|(s, l)| (s, Lexem::sub(l)))
}

fn text(i: &str) -> IResult<&str, Lexem> {
    let stop = |c| c == '{';
    take_till(stop)(i).map(|(s, t)| (s, Lexem::plain(t)))
}

fn template(i: &str) -> IResult<&str, Vec<Lexem>> {
    many_till(alt((sub, text)), eof)(i).map(|(s, (v, _))| (s, v))
}

pub(super) fn parse_template(s: &str) -> Result<Vec<Lexem>> {
    template(s)
        // TODO: return error if remaining string is not empty
        .map(|(_, v)| v)
        .map_err(|e| CrateError::InvalidPattern(e.to_string()))
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn sub_test() {
        assert_eq!(sub("{ab_c}"), Ok(("", Lexem::sub("ab_c"))));
        assert!(sub("{ab-c}").is_err());
    }
    #[test]
    fn text_test() {
        assert_eq!(text("text{tag}"), Ok(("{tag}", Lexem::plain("text"))));
        assert_eq!(text("text/{tag}"), Ok(("{tag}", Lexem::plain("text/"))));
        assert_eq!(text("text"), Ok(("", Lexem::plain("text"))));
    }
    #[test]
    fn template_test() {
        let mut expected = vec![
            Lexem::sub("a"),
            Lexem::plain("/"),
            Lexem::sub("text"),
            Lexem::plain("."),
            Lexem::sub("ext"),
        ];
        assert_eq!(template("{a}/{text}.{ext}"), Ok(("", expected.clone())));
        expected.insert(0, Lexem::plain("http://"));
        assert_eq!(template("http://{a}/{text}.{ext}"), Ok(("", expected)));
    }
}
