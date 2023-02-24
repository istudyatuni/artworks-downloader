use nom::{
    branch::alt,
    bytes::complete::{tag, take_till, take_while},
    combinator::eof,
    multi::many_till,
    sequence::delimited,
    IResult,
};

use crate::{CrateError, Result};

use super::Lexem;

fn sub(i: &str) -> IResult<&str, Lexem> {
    let is_key = |c: char| c.is_alphabetic() || c == '_';
    delimited(tag("{"), take_while(is_key), tag("}"))(i).map(|(s, l)| (s, Lexem::sub(l)))
}

fn text(i: &str) -> IResult<&str, Lexem> {
    take_till(|c| "{/".contains(c))(i).map(|(s, t)| (s, Lexem::plain(t)))
}

fn segment(i: &str) -> IResult<&str, Vec<Lexem>> {
    many_till(alt((sub, text)), alt((tag("/"), eof)))(i).map(|(s, (v, _))| (s, v))
}

fn path(i: &str) -> IResult<&str, Vec<Lexem>> {
    many_till(segment, eof)(i).map(|(s, (v, _))| (s, v.join(&Lexem::sep())))
}

pub fn parse_template(s: &str) -> Result<Vec<Lexem>> {
    path(s)
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
        assert_eq!(text("text/{tag}"), Ok(("/{tag}", Lexem::plain("text"))));
        assert_eq!(text("text"), Ok(("", Lexem::plain("text"))));
    }
    #[test]
    fn segment_test() {
        assert_eq!(
            segment("{ab_c} - text - {test}{text}"),
            Ok((
                "",
                vec![
                    Lexem::sub("ab_c"),
                    Lexem::plain(" - text - "),
                    Lexem::sub("test"),
                    Lexem::sub("text"),
                ]
            ))
        );
    }
    #[test]
    fn path_test() {
        assert_eq!(
            path("{a}/{text}.{ext}"),
            Ok((
                "",
                vec![
                    Lexem::sub("a"),
                    Lexem::sep(),
                    Lexem::sub("text"),
                    Lexem::plain("."),
                    Lexem::sub("ext"),
                ]
            ))
        );
    }
}
