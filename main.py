import aiohttp
import asyncio
import questionary
from parsel.selector import Selector
from pprint import pprint
import dotenv
import os
from tqdm import tqdm
import aiofiles
from pathlib import Path
from alive_progress import alive_it


async def main():
    dotenv.load_dotenv()
    cookies = os.getenv("COOKIES")
    headers = {
        "Referer": "https://cursos.alura.com.br/discover",
        "Alt-Used": "cursos.alura.com.br",
        "Cookie": cookies,
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(
            url="https://cursos.alura.com.br/courses/filtered?categoryUrlName=programacao",
        ) as response:
            text = await response.text()
            doc = Selector(text=text)
            cursos = doc.css(".card-list__item")
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
        modules_counter = 0
        for module in modules:
            module_name = module.css(".bootcamp-text-color::text").get()
            formated_module_name = f"{modules_counter:02d} | {module_name.strip()}"
            if not module_name:
                continue
            module_link = module.attrib["href"]

            await module_downloader_handler(
                session, module_link, formated_module_name, course_link
            )
            modules_counter += 1


async def module_downloader_handler(
    session: aiohttp.ClientSession, module_link: str, module_name: str, course_link: str
):
    url = f"https://cursos.alura.com.br{module_link}"
    async with session.get(url) as response:
        text = await response.text()
        doc = Selector(text=text)

        menu_items = doc.css(".task-menu-nav-item a")

        item_counter = 0
        for item in tqdm(menu_items, desc=f"Baixando {module_name}"):
            item_name = item.css(".task-menu-nav-item-title::text").get()
            item_link = item.attrib["href"]
            item_class = item.attrib["class"]

            if "VIDEO" in item_class:
                video_name = f"{item_counter:02d} | {item_name.strip()}"
                await video_downloader_handler(
                    session,
                    video_link=item_link,
                    video_name=video_name,
                    module_name=module_name,
                    course_name=course_link.replace("/course/", ""),
                )
                item_counter += 1


async def video_downloader_handler(
    session: aiohttp.ClientSession,
    video_link: str,
    video_name: str,
    module_name: str,
    course_name: str,
):

    url = f"https://cursos.alura.com.br{video_link}"

    video_api_url = f"{url}/video"
    mp4 = await get_video_mp4(
        session,
        video_api_url,
    )

    await final_download(
        session,
        mp4,
        video_name,
        module_name,
        await format_from_slug(course_name),
    )


async def get_video_mp4(session: aiohttp.ClientSession, url: str):
    async with session.get(url) as response:
        data = await response.json()
        mp4 = data[0]["mp4"]
        return mp4


async def final_download(
    session: aiohttp.ClientSession,
    mp4: str,
    video_name: str,
    module_name: str,
    couse_name: str,
):
    path = Path(f"Alura Downloader/{couse_name}/{module_name}/{video_name}/video.mp4")
    os.makedirs(path.parent, exist_ok=True)
    async with session.get(mp4) as response:
        async with aiofiles.open(path, "wb") as f:
            await f.write(await response.read())


async def format_from_slug(slug: str):
    return " ".join([word.capitalize() for word in slug.split("-")]).replace("/", "-")


if __name__ == "__main__":
    asyncio.run(main())
