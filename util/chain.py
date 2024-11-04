from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from util.constants import DEFAULT_MODEL


def set_map_chain():
    llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=0)
    map_template = """
    You are a helpful assistant that aids in extracting potential hot clip segments from YouTube video scripts based on the characteristics of {category} content.
    When analyzing the transcript, please consider the following format:

    [0] First segment of the video (0-60 seconds)
    [1] Second segment of the video (60-120 seconds)
    [2] Third segment of the video (120-180 seconds)
    ...and so on.

    Based on the transcript of the video, please provide TWO segment numbers that you think are potential hot clip segments.
    You should only extract the '[number]' segments included in the INPUT text.
    If you cannot find any potential hot clip segments, please return '-1'.

    Example:

    INPUT
    [0] text
    [1] text(if you select this segment)
    [2] text
    [3] text(if you select this segment)

    OUTPUT
    1,3
    ----
    INPUT
    {text}

    OUTPUT
    """
    map_prompt = PromptTemplate.from_template(map_template)

    map_chain = map_prompt | llm | StrOutputParser()

    return map_chain


def set_reduce_chain():
    llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=0)
    reduce_template = """
    You are a helpful assistant that aids in extracting potential hot clip segments from YouTube video scripts based on the characteristics of {category} content.
    INPUT text is a concatenation of the selected segments from the previous MAP step.
    Please extract the maximum {target_count} most important and interesting segments from the INPUT text(['number']).

    Example:

    INPUT
    [0] text
    [1] text
    [2] text(if you select this segment)
    [3] text(if you select this segment)
    [4] text(if you select this segment)
    [5] text(if you select this segment)
    [6] text(if you select this segment)

    OUTPUT
    2,3,4,5,6

    INPUT
    {text}

    OUTPUT
    """
    reduce_prompt = PromptTemplate.from_template(reduce_template)
    reduce_chain = reduce_prompt | llm | StrOutputParser()

    return reduce_chain


def set_title_chain():
    """클립 제목 생성을 위한 체인 설정"""
    llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=0.7)  # 약간의 창의성을 위해 temperature 조정
    
    title_template = """
    You are a helpful assistant that creates engaging YouTube clip titles.
    Based on the transcript and category of the video clip, create a catchy and descriptive Korean title.
    The title should be between 10 and 30 characters.
    
    Category: {category}
    Transcript: {text}
    
    Generate a title that:
    1. Captures the main point or highlight of the clip
    2. Uses engaging language appropriate for YouTube
    3. Maintains the original context and tone
    4. Includes relevant keywords
    5. Corrects any spelling or typographical errors in the transcript appropriately
    
    OUTPUT FORMAT: Just return the title without any explanations or quotes.
    """
    
    title_prompt = PromptTemplate.from_template(title_template)
    title_chain = title_prompt | llm | StrOutputParser()
    
    return title_chain
