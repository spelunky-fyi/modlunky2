use http::{header::AUTHORIZATION, Request, Response};
use hyper::Body;
use hyper_tls::HttpsConnector;
use tower::{util::BoxCloneService, ServiceBuilder};
use tower_http::{
    classify::{NeverClassifyEos, ServerErrorsFailureClass},
    trace::{DefaultOnBodyChunk, DefaultOnEos, DefaultOnFailure, ResponseBody},
    ServiceBuilderExt,
};

pub type TracedResponse<B> = ResponseBody<
    B,
    NeverClassifyEos<ServerErrorsFailureClass>,
    DefaultOnBodyChunk,
    DefaultOnEos,
    DefaultOnFailure,
>;

/// The concerete type of the returned client.
pub type HttpClient = BoxCloneService<Request<Body>, Response<TracedResponse<Body>>, hyper::Error>;

/// Creates a new HttpClient. It's preferable to share or clone an existing client, when possible.
/// The underlying connection pool will be reused.
pub fn new_http_client() -> HttpClient {
    let inner_client =
        hyper::client::Client::builder().build::<_, hyper::Body>(HttpsConnector::new());
    ServiceBuilder::new()
        .boxed_clone()
        .sensitive_headers([AUTHORIZATION])
        .trace_for_http()
        .follow_redirects()
        .service(inner_client)
}
