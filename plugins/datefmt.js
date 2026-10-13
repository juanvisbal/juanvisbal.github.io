// datefmt formats an RFC 3339 date ("2026-10-09T21:15:14-05:00") without changing its time zone,
// or converted to `offset` (e.g. "-05:00") when given.
//
// Tokens: yyyy, MMM (Oct), MM (10), M, dd (09), d (9), HH (21), h (9), mm, ss, a (PM), ZZZZZ (-05:00)
//
// usage: ${ datefmt(post.created_at, "MMM d, yyyy") }
//        ${ datefmt(reply.date_published, "h:mm a", "-05:00") }
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export default function datefmt(date, format, offset) {
    const m = /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(?:\.\d+)?(Z|[+-]\d\d:?\d\d)$/.exec(String(date || ""));
    if (!m) return date ? String(date) : "";
    let [, y, mo, d, h, mi, s, zone] = m;
    zone = zone === "Z" ? "+00:00" : zone.length === 5 ? zone.slice(0, 3) + ":" + zone.slice(3) : zone;
    if (offset && offset !== zone) {
        const minutes = (z) => (z[0] === "-" ? -1 : 1) * (Number(z.slice(1, 3)) * 60 + Number(z.slice(4, 6)));
        const utc = Date.UTC(+y, +mo - 1, +d, +h, +mi, +s) - minutes(zone) * 60000;
        const t = new Date(utc + minutes(offset) * 60000);
        const pad = (n) => String(n).padStart(2, "0");
        [y, mo, d, h, mi, s, zone] = [String(t.getUTCFullYear()), pad(t.getUTCMonth() + 1), pad(t.getUTCDate()),
            pad(t.getUTCHours()), pad(t.getUTCMinutes()), pad(t.getUTCSeconds()), offset];
    }
    const hour = Number(h);
    const values = {
        yyyy: y, MMM: MONTHS[Number(mo) - 1], MM: mo, M: String(Number(mo)), dd: d, d: String(Number(d)),
        HH: h, h: String(hour % 12 || 12), mm: mi, ss: s, a: hour < 12 ? "AM" : "PM", ZZZZZ: zone,
    };
    return String(format || "yyyy-MM-ddTHH:mm:ssZZZZZ").replace(/yyyy|MMM|MM|M|dd|d|HH|h|mm|ss|a|ZZZZZ/g, (t) => values[t]);
}
