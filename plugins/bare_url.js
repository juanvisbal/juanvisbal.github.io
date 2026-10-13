// bare_url drops the scheme and trailing slash: "https://sltwtr.com/" -> "sltwtr.com"
//
// usage: ${ bare_url(item.url) }
export default function bare_url(url) {
    return String(url || "").replace(/^https?:\/\//, "").replace(/\/$/, "");
}
