from pydantic import BaseModel
from typing import List, Dict, Optional

class BaseRequest(BaseModel):
    class Config:
        extra = "allow"

class LoginRequest(BaseRequest):
    ApplicationVersion: int
    AuthorizationCode: str
    IssuerId: int
    LanguageId: int
    MessageId: str
    NatType: int
    PlatformAccountId: str
    RegionId: int

class SimpleRequest(BaseRequest):
    MessageId: str
    SessionId: str
    UserId: int

class EmergencyNoticeRequest(BaseRequest):
    CheckTime: str
    Language: int
    MessageId: str
    Region: int
    SessionId: str
    UserId: int

class BloodMessCreateRequest(BaseRequest):
    BloodMessList: List[Dict]
    CharaId: int
    MessageId: str
    SessionId: str
    UserId: int

class BloodMessGetListRequest(BaseRequest):
    AreaInfoList: List[Dict]
    BloodDataVersion: int
    CharaDataVersion: int
    GetMaxCount: int
    MessShellInfoVersion: int
    MessageId: str
    SessionId: str
    UserId: int

class BloodMessGetEvaluateRequest(BaseRequest):
    BloodMessIdList: List[int]
    MessageId: str
    SessionId: str
    UserId: int

class BloodMessSearchAddRequest(BaseRequest):
    BloodMessIdList: List[int]
    CharaId: int
    MessageId: str
    SessionId: str
    UserId: int

class BloodMessEvaluateRequest(BaseRequest):
    BloodMessId: int
    EvaluateKind: int
    MessageId: str
    SessionId: str
    UserId: int

class TombMessGetListRequest(BaseRequest):
    AreaInfoList: List[Dict]
    GetMaxCount: int
    MessShellInfoVersion: int
    MessageId: str
    SessionId: str
    TombDataVersion: int
    UserId: int

class TombMessCreateRequest(BaseRequest):
    AreaId: int
    AreaRegionId: int
    ChannelId: int
    CharaId: int
    DeathVisionData: str
    DeathVisionDataVersion: int
    MessageId: str
    SessionId: str
    TombData: str
    TombDataVersion: int
    UserId: int

class DeathVisionGetRequest(BaseRequest):
    DeathVisionDataVersion: int
    MessageId: str
    SessionId: str
    TombMessId: int
    UserId: int

class WanderingGhostCreateRequest(BaseRequest):
    AreaId: int
    AreaRegionId: int
    ChannelId: int
    CharaId: int
    MatchingLevel: int
    MessageId: str
    RejectIgnore: int
    SessionId: str
    UserId: int
    WanderingGhostData: str
    WanderingGhostDataVersion: int

class WanderingGhostGetRequest(BaseRequest):
    AreaList: List[Dict]
    GetMaxCount: int
    JoinedCharaIdList: List[Dict]
    MatchingLevel: int
    MessageId: str
    SessionId: str
    UserId: int
    WanderingGhostDataVersion: int

class ChairMessGetRequest(BaseRequest):
    CharaId: int
    MessageId: str
    SessionId: str
    UserId: int
    WarpInfoList: List[Dict]

class ChairRespawnNoticeRequest(BaseRequest):
    ChannelId: int
    CharaId: int
    MessageId: str
    SessionId: str
    UserId: int
    WarpInfoId: int

class ChannelSearchRequest(BaseRequest):
    FixedOrGeneralList: List[Dict]
    FormDataVersion: int
    GetCount: int
    HolyGrailTypeId: Optional[int] = None
    MessageId: str
    RitualLevel: Optional[int] = None
    SessionId: str
    Status: int
    SubFeatureFlag: Optional[int] = None
    UnlockedFlagList: List[Dict]
    UserId: int

class ChannelGetDetailsInfoRequest(BaseRequest):
    ChannelIdList: List[Dict]
    MessageId: str
    SessionId: str
    UserId: int

class ChannelUploadRequest(BaseRequest):
    CharaId: int
    FixedOrGeneral: int
    FormData: str
    FormDataVersion: int
    HolyGrailTypeId: int
    MessageId: str
    RitualLevel: int
    SessionId: str
    ShareLevel: int
    Status: int
    SubFeatureFlag: int
    UnlockFlagList: List[Dict]
    UserId: int
    WishMaterialList: List[Dict]

class ChannelGetInfoRequest(BaseRequest):
    ChannelIdList: List[Dict]
    MessageId: str
    SessionId: str
    UserId: int

class ChannelWordSearchRequest(BaseRequest):
    FormDataVersion: int
    MessageId: str
    SearchWord: str
    SessionId: str
    UnlockedFlagList: List[Dict]
    UserId: int

class ChannelRandomJoinRequest(BaseRequest):
    CharaId: int
    FormDataVersion: int
    MessageId: str
    RandomJoinTargetList: List[Dict]
    SessionId: str
    UnlockedFlagList: List[Dict]
    UserId: int

class MessengerShellUploadRequest(BaseRequest):
    CharaId: int
    MessageId: str
    SessionId: str
    ShellData: str
    ShellDataVersion: int
    UserId: int

class UserPropertiesMoveCountCheckRequest(BaseRequest):
    Count: int
    MessageId: str
    SessionId: str
    UserId: int

class UserPropertiesMoveCountRequest(BaseRequest):
    Count: int
    MessageId: str
    SessionId: str
    UserId: int


class BloodMessRemoveRequest(BaseRequest):
    BloodMessIdList: List[int]
    MessageId: str
    SessionId: str
    UserId: int


class TombMessRemoveRequest(BaseRequest):
    MessageId: str
    SessionId: str
    TombMessId: int
    UserId: int


class ChannelShareRequest(BaseRequest):
    ChannelId: Optional[int] = None
    ChannelIdList: Optional[List[Dict]] = None
    MessageId: str
    SessionId: str
    ShareLevel: int
    UserId: int


class ChannelAddMaterialRequest(BaseRequest):
    ChannelId: Optional[int] = None
    ChannelIdList: Optional[List[Dict]] = None
    MaterialList: List[Dict]
    MessageId: str
    SessionId: str
    UserId: int


class ChannelAddMaterialCompleteNotifyRequest(BaseRequest):
    ChannelId: Optional[int] = None
    ChannelIdList: Optional[List[Dict]] = None
    MessageId: str
    SessionId: str
    SpendMaterialCount: Optional[int] = None
    UserId: int


class MultiPlayNetErrorRequest(BaseRequest):
    MessageId: str
    SessionId: str
    UserId: int