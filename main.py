import aiohttp
import asyncio
import questionary
from parsel.selector import Selector
from pprint import pprint
import nodriver as uc


async def login():
    email = input("Digite a email: ")
    password = input("Digite o senha: ")

    if not email or not password:
        raise ValueError("Email and password are required.")

    browser = await uc.start(
        headless=True,
        browser_executable_path="/snap/bin/chromium",
    )
    login_form_url = "https://cursos.alura.com.br/loginForm"

    login_page = await browser.get(login_form_url)

    email_input = await login_page.select("#login-email")
    password_input = await login_page.select("#password")
    login_btn = await login_page.select(".btn-login")

    await email_input.send_keys(email)
    await password_input.send_keys(password)
    await login_btn.click()

    await login_page

    cookies = await browser.cookies.get_all(requests_cookie_format=True)
    browser.stop()

    return cookies


async def main():
    cookies = await login()
    cookie_string = "; ".join(f"{cookie.name}={cookie.value}" for cookie in cookies)
    headers = {
        "Referer": "https://cursos.alura.com.br/discover",
        "Alt-Used": "cursos.alura.com.br",
        "Cookie": cookie_string,
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(
            url="https://cursos.alura.com.br/courses/filtered",
            params={"categoryUrlName": "programacao"},
        ) as response:
            text = await response.text()
            doc = Selector(text=text)

            cursos = doc.css(".card-list__item")
            print(len(cursos))
            selecionados = await questionary.checkbox(
                "Seleciona os cursos",
                choices=[c.attrib["data-course-name"] for c in cursos],
            ).ask_async()

            for curso in selecionados:
                course_block = doc.css(f".card-list__item[data-course-name='{curso}']")

                course_link = course_block.css("a::attr(href)").get()
                await course_downloader_handler(session, course_link)


async def course_downloader_handler(session: aiohttp.ClientSession, course_link: str):
    url = f"https://cursos.alura.com.br{course_link}"
    async with session.get(url) as response:
        text = await response.text()
        doc = Selector(text=text)

        modules = doc.css(".courseSection-listItem a")
        for module in modules:
            module_name = module.css(".bootcamp-text-color::text").get()
            if not module_name:
                continue
            module_link = module.attrib["href"]

            await module_downloader_handler(session, module_link, module_name.strip())


async def module_downloader_handler(
    session: aiohttp.ClientSession, module_link: str, module_name: str
):
    url = f"https://cursos.alura.com.br{module_link}"
    async with session.get(url) as response:
        text = await response.text()
        doc = Selector(text=text)

        print(f"Module: {module_name}")
        menu_items = doc.css(".task-menu-nav-item a")
        for item in menu_items:
            item_name = item.css(".task-menu-nav-item-title::text").get()
            item_link = item.attrib["href"]
            item_class = item.attrib["class"]

            if "VIDEO" in item_class:
                await video_downloader_handler(session, item_link, item_name.strip())


async def video_downloader_handler(
    session: aiohttp.ClientSession, video_link: str, video_name: str
):
    url = f"https://cursos.alura.com.br{video_link}"
    async with session.get(url) as response:
        text = await response.text()
        doc = Selector(text=text)

        video_url = f"{url}/video"
        mp4 = await get_video_json(session, video_url)
        pprint(
            {
                "video_name": video_name,
                "video_url": mp4,
            }
        )


async def get_video_json(session: aiohttp.ClientSession, url: str):
    async with session.get(url) as response:
        data = await response.json()
        mp4 = data[-1]["mp4"]
        return mp4


if __name__ == "__main__":
    asyncio.run(main())
