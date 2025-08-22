import asyncio
import csv
import random
import time
from playwright.async_api import async_playwright


async def scrape_game_rankings():
    # 결과 저장용 리스트
    results = []
    output_file = "game_rankings.csv"

    # CSV 헤더 설정
    with open(output_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Rank", "Game Name", "Tags"])

    async with async_playwright() as p:
        # User-Agent 목록
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
        ]

        # 브라우저 설정 (헤드리스 모드, User-Agent, 스텔스 설정)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={"width": 1280, "height": 720},
            java_script_enabled=True,
            # 추가 스텔스 설정
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "DNT": "1",  # Do Not Track
            },
        )

        page = await context.new_page()

        # 추가 스텔스: WebGL, Canvas 지문 방지
        await page.evaluate(
            """
            () => {
                // WebGL 비활성화
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37446) return 'Intel Inc.';
                    if (parameter === 37447) return 'Intel Iris OpenGL Engine';
                    return getParameter(parameter);
                };
                // Navigator 속성 수정
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
            }
        """
        )

        # 대상 URL로 이동
        await page.goto(
            "https://sj.qq.com/wechat-game/best-sell-game-rank", timeout=60000
        )
        await page.wait_for_load_state("networkidle")

        # 스크롤 및 데이터 추출
        last_height = await page.evaluate("document.body.scrollHeight")
        while True:
            # 게임 카드 요소 선택
            game_cards = await page.query_selector_all(".GameList_gameCard__ODNEs")
            for card in game_cards:
                try:
                    # 랭킹
                    rank_elem = await card.query_selector(".GameCard_rankNumber__kn4_s")
                    rank = await rank_elem.inner_text() if rank_elem else "N/A"

                    # 게임명
                    name_elem = await card.query_selector(".GameCard_name___MG5g")
                    game_name = await name_elem.inner_text() if name_elem else "N/A"

                    # 태그
                    tag_elems = await card.query_selector_all(".TagList_tagName__Gf5n2")
                    tags = (
                        [await tag.inner_text() for tag in tag_elems]
                        if tag_elems
                        else []
                    )
                    tags_str = ", ".join(tags)

                    # 결과 저장
                    result = {"Rank": rank, "Game Name": game_name, "Tags": tags_str}
                    if result not in results:  # 중복 방지
                        results.append(result)

                        # 중간 저장 (CSV)
                        with open(
                            output_file, mode="a", newline="", encoding="utf-8"
                        ) as file:
                            writer = csv.writer(file)
                            writer.writerow([rank, game_name, tags_str])

                        print(f"Scraped: {result}")

                except Exception as e:
                    print(f"Error processing card: {e}")

            # 스크롤
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(random.randint(2000, 5000))  # 랜덤 대기 (2~5초)

            # 새로운 높이 확인
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                print("Reached end of scroll")
                break
            last_height = new_height

        # 최종 JSON 저장
        with open("game_rankings.json", mode="w", encoding="utf-8") as file:
            json.dump(results, file, ensure_ascii=False, indent=2)

        await browser.close()

    return results


if __name__ == "__main__":
    asyncio.run(scrape_game_rankings())
