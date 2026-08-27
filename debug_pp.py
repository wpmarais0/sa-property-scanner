from bs4 import BeautifulSoup
import json

html = """
<html><body>
<script type="application/ld+json">
{
    "@type": "Residence",
    "address": {"addressLocality": "Somerset West"},
    "additionalProperty": [{"name": "Bedrooms", "value": "2"}],
    "url": "https://www.privateproperty.co.za/for-sale/western-cape/T9999999"
}
</script>
</body></html>
"""

soup = BeautifulSoup(html, "html.parser")
scripts = soup.find_all("script", type="application/ld+json")
print("Scripts:", len(scripts))
for script in scripts:
    print("script.string:", repr(script.string))
    data = json.loads(script.string)
    print("@type:", data.get("@type"))
    url = data.get("url", "")
    external_id = url.rstrip("/").split("/")[-1]
    print("external_id:", external_id)
    
    link = soup.find("a", href=lambda h: h and external_id in h)
    print("link:", link)
    if link:
        print("link found")
    else:
        print("link NOT found")
    
    # Simulate _parse_residence logic
    if not external_id:
        print("skip: no external_id")
        continue
    
    from sa_property_scanner.sources.private_property import PrivatePropertySource
    source = PrivatePropertySource(search_url="https://example.com")
    result = source._parse_residence(data, soup)
    print("_parse_residence result:", result)
