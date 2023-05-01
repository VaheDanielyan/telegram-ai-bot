import openai
from enum import Enum

class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class ImageResolution(Enum):
    SMALL="256x256"
    MEDIUM="512x512"
    LARGE="1024x1024"

class UsageType(Enum):
    CHAT = "chatgpt"
    IMAGE = "dalle"
    VOICE = "whisper"

class IntegrationOpenAI:

    def __init__(self, api_key):
        openai.api_key = api_key

    def gptCompletion(self, message: str, system_prompt: str, user_name, model: str, user_data = {}):
        self.updateContext(user_data, message, MessageRole.USER)
        systemPrompt = [self.getMessage(MessageRole.SYSTEM, f"You are chatting with {user_name}. {system_prompt}")]
        fullMessage = systemPrompt + user_data["context"]
        try:
            response = openai.ChatCompletion.create(
                model = model,
                messages = fullMessage,
                temperature = user_data["options"]["temperature"],
            )
        except Exception as e:
            print(e)
            return f"There was a problem with OpenAI, so I can't answer you: \n\n{e}"

        assistant_message = response.get('choices')[0].get('message').get("content")
        self.updateContext(user_data, assistant_message, MessageRole.ASSISTANT)
        self.updateUsage(user_data, UsageType.CHAT, response.get('usage')["total_tokens"])
        if (assistant_message == None):
            return f"OpenAI returned nothing, maybe usage limit exceeded?"    
        return assistant_message

    def generateImage(self, user_data, image_prompt, resolution: ImageResolution):
        self.updateUsage(user_data, UsageType.IMAGE, 1)
        response = openai.Image.create(
            prompt=image_prompt,
            n=1,
            size=resolution.value
        )
        try:
            image_url = response['data'][0]['url']
        except Exception as e:
            return "Error generating. Your prompt may contain text that is not allowed by OpenAI safety system."
        return image_url

    def transcribeAudio(self, user_data, audio_file, duration):
        self.updateUsage(user_data, UsageType.VOICE, duration)
        try:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
        except Exception as e:
            print(e)
            transcript = "Transcript failed."
        return transcript

    def getMessage(self, role : MessageRole, text: str):
        return {"role": role.value, "content": text}

    def updateContext(self, user_data, message, contextType: MessageRole):
        user_data['context'].append(self.getMessage(contextType, message))
        if len(user_data['context']) > user_data["options"]["max-context"]:
            user_data['context'].pop(0)

    def updateUsage(self, user_data, usageType: UsageType, usageCost):
        user_data["usage"][usageType.value] += usageCost

