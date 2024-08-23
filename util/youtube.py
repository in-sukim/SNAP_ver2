from youtube_transcript_api import YouTubeTranscriptApi
from kiwipiepy import Kiwi
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver


class YouTubeVideo:
    def __init__(self, video_url):
        self.video_url = video_url
        self.video_id = self.get_video_id(video_url)
        self.category = self.get_category()
        self.transcript = self.get_transcript()
        self.shorts_group = self.get_shorts_group()
        self.fix_sentences_shorts_group = self.get_fix_sentences_shorts_group()

    def get_video_id(self, video_url):
        video_id = video_url.split("v=")[1][:11]
        return video_id

    def get_transcript(self, languages="ko"):
        try:
            transcript = YouTubeTranscriptApi.get_transcript(
                self.video_id, languages=[languages]
            )
        except:
            languages = "en"
            transcript = YouTubeTranscriptApi.get_transcript(
                self.video_id, languages=[languages]
            )
        return transcript

    def get_category(self):
        """
        유튜브 영상 카테고리 반환
        Args:
            video_url: 유튜브 영상 URL
            user_agent: User-Agent
        Returns:
            category: 유튜브 영상 카테고리
        """
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        # User-Agent로 변경
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"user-agent={user_agent}")
        driver = webdriver.Chrome(options=options)

        driver.get(self.video_url)

        html = driver.page_source
        category = html.split('"category":"')[1].split('",')[0]
        return category

    def get_shorts_group(self):
        """
        60초 이내 구간으로 스크립트 그룹화.
        Args:
            transcript: 유튜브 영상 자막 (List of dictionary)
                - text: 자막 텍스트
                - start: 자막 시작 시간
                - duration: 자막 지속 시간
        Returns:
            shorts: 60초 이내 구간으로 스크립트 그룹화된 dictionary
                - key: 60초 이내 구간 index(0부터 시작)
                - value: 60초 이내 구간의 자막 텍스트
        """
        shorts = {}
        for i in range(len(self.transcript)):
            trans = self.transcript[i]
            text, start, duration = trans["text"], trans["start"], trans["duration"]
            shorts_group = int(start // 60)
            if shorts_group not in shorts:
                shorts[shorts_group] = []
            shorts[shorts_group] += [text]
        shorts = {key: " ".join(text) for key, text in shorts.items()}
        return shorts

    def get_fix_sentences_shorts_group(self):
        """
        shorts_group 구간 별 text 문장 "\n"으로 구분하여 반환
        Args:
            shorts_group: 60초 이내 구간으로 스크립트 그룹화된 dictionary
                - key: 60초 이내 구간 index(0부터 시작)
                - value: 60초 이내 구간의 자막 텍스트
        Returns:
            fix_shorts_gorup: value 문장 "\n"으로 구분하여 반환
                - key: 60초 이내 구간 index(0부터 시작)
                - value: 60초 이내 구간의 자막 문장 분할(kiwi)을 통해 "\n"으로 구분된 텍스트
        """

        kiwi = Kiwi()
        for key, sentence in self.shorts_group.items():
            split_sentences = kiwi.split_into_sents(sentence)
            fix_sencences = ""
            for sen in split_sentences:
                fix_sencences += sen.text + "\n"
            self.shorts_group[key] = fix_sencences
        return self.shorts_group


if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=4JdzuB702wI"
    video = YouTubeVideo(video_url)
    video_id = video.video_id
    category = video.category
    transcript = video.transcript
    shorts_group = video.shorts_group

    print(
        f"Video ID: {video_id}\nCategory: {category}\nShorts Group Example: {shorts_group[0]}"
    )
