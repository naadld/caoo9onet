addEventListener("fetch", event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const url = new URL(request.url);

  // Handle CORS preflight requests
  if (request.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Max-Age": "86400",
      },
    });
  }

  // Path pattern: /cdn/<hostname>/<remaining_path...>
  if (url.pathname.startsWith("/cdn/")) {
    const parts = url.pathname.slice(5).split("/");
    const targetHost = parts[0];
    const targetPath = parts.slice(1).join("/");
    
    if (!targetHost) {
      return new Response("Missing target hostname", { status: 400 });
    }

    // Construct target URL
    const targetUrl = new URL(`https://${targetHost}/${targetPath}${url.search}`);

    // Setup headers to mimic o9o.net requests to bypass CDN security
    const headers = new Headers(request.headers);
    headers.set("Host", targetHost);
    headers.set("Origin", "https://www.o9o.net");
    headers.set("Referer", "https://www.o9o.net/");

    try {
      const response = await fetch(targetUrl.toString(), {
        method: request.method,
        headers: headers,
        redirect: "follow",
      });

      // Copy response headers and add CORS headers
      const newHeaders = new Headers(response.headers);
      newHeaders.set("Access-Control-Allow-Origin", "*");
      newHeaders.set("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS");
      newHeaders.set("Access-Control-Expose-Headers", "*");
      
      // Remove frame restrictions
      newHeaders.delete("x-frame-options");
      newHeaders.delete("content-security-policy");

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: newHeaders,
      });
    } catch (err) {
      return new Response(`Proxy Error: ${err.message}`, { status: 500 });
    }
  }

  return new Response("Prinberk HP Abeka Proxy is active.", {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
