import requests

url = 'https://www.google.com/search?q=it+companies+in+indore&sca_esv=2848611885b4dcac&sxsrf=AHTn8zqHFDwPzodlGGLBz2u6i20R_4p07w%3A1746879969559&source=hp&ei=4UUfaMz1H-Od4-EPksbnuAM&iflsig=ACkRmUkAAAAAaB9T8a4_jeTapjNLxka0OszA80RJt-wS&oq=it+com&gs_lp=Egdnd3Mtd2l6IgZpdCBjb20qAggAMgUQABiABDILEAAYgAQYkgMYigUyBRAAGIAEMggQABiABBixAzIIEC4YgAQYsQMyCBAAGIAEGMkDMgUQABiABDIIEAAYgAQYsQMyBRAAGIAEMgUQABiABEiUNVCsGViWInACeACQAQCYAfwBoAG2CaoBBTAuMy4zuAEDyAEA-AEBmAIIoAK1CqgCCsICBxAjGCcY6gLCAgoQIxiABBgnGIoFwgILEAAYgAQYsQMYgwHCAgsQLhiABBixAxiDAcICDhAAGIAEGLEDGIMBGIoFwgIREC4YgAQYsQMY0QMYgwEYxwHCAgQQIxgnwgIQEC4YgAQYxwEYJxiKBRivAcICBBAAGAPCAgsQLhiABBjHARivAcICCxAuGIAEGLEDGNQCmAMX8QVOWrheRVt5p5IHBTIuMi40oAeISrIHBTAuMi40uAeRCg&sclient=gws-wiz'
proxy = 'geo.iproyal.com:12321'
proxy_auth = 'vnkl9BGvMRlmvWfO:EjFoKHcjcchVYwZ9_country-in'
proxies = {
   'http': f'http://{proxy_auth}@{proxy}',
   'https': f'http://{proxy_auth}@{proxy}'
}

response = requests.get(url, proxies=proxies)
print(response.text)
print(response.status_code)