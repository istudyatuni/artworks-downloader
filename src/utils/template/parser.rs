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

fn text<'a>(i: &'a str, exclude: &'a str) -> IResult<&'a str, Lexem> {
    take_till(|c| exclude.contains(c))(i).map(|(s, t)| (s, Lexem::plain(t)))
}

fn path_text(i: &str) -> IResult<&str, Lexem> {
    text(i, "{/")
}

fn path_segment(i: &str) -> IResult<&str, Vec<Lexem>> {
    many_till(alt((sub, path_text)), alt((tag("/"), eof)))(i).map(|(s, (v, _))| (s, v))
}

fn path_template(i: &str) -> IResult<&str, Vec<Lexem>> {
    many_till(path_segment, eof)(i).map(|(s, (v, _))| (s, v.join(&Lexem::sep())))
}

pub(super) fn parse_path_template(s: &str) -> Result<Vec<Lexem>> {
    path_template(s)
        // TODO: return error if remaining string is not empty
        .map(|(_, v)| v)
        .map_err(|e| CrateError::InvalidPattern(e.to_string()))
}

fn any_text(i: &str) -> IResult<&str, Lexem> {
    text(i, "{")
}

fn any_template(i: &str) -> IResult<&str, Vec<Lexem>> {
    many_till(alt((sub, any_text)), eof)(i).map(|(s, (v, _))| (s, v))
}

pub(super) fn parse_any_template(s: &str) -> Result<Vec<Lexem>> {
    any_template(s)
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
        assert_eq!(text("text{tag}", "{/"), Ok(("{tag}", Lexem::plain("text"))));
        assert_eq!(
            text("text/{tag}", "{/"),
            Ok(("/{tag}", Lexem::plain("text")))
        );
        assert_eq!(text("text", "{/"), Ok(("", Lexem::plain("text"))));
    }
    #[test]
    fn segment_test() {
        assert_eq!(
            path_segment("{ab_c} - text - {test}{text}"),
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
            path_template("{a}/{text}.{ext}"),
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
    #[test]
    fn any_test() {
        assert_eq!(
            any_template("http://{a}/{text}.{ext}"),
            Ok((
                "",
                vec![
                    Lexem::plain("http://"),
                    Lexem::sub("a"),
                    Lexem::plain("/"),
                    Lexem::sub("text"),
                    Lexem::plain("."),
                    Lexem::sub("ext"),
                ]
            ))
        );
    }
}
