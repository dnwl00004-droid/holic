from src.providers.sec_activity import parse_form4_xml
from src.providers.institutional13f import normalize_name


def test_form4_parser():
    xml="""<ownershipDocument>
    <reportingOwner><reportingOwnerId><rptOwnerName>Jane Doe</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isDirector>1</isDirector><isOfficer>0</isOfficer></reportingOwnerRelationship></reportingOwner>
    <nonDerivativeTable><nonDerivativeTransaction>
      <transactionDate><value>2026-09-01</value></transactionDate>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>1000</value></transactionShares>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
        <transactionPricePerShare><value>25.5</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>"""
    x=parse_form4_xml(xml)
    assert x["owner"]=="Jane Doe"
    assert x["transactions"][0]["code"]=="P"
    assert x["transactions"][0]["value"]==25500


def test_name_normalization():
    assert normalize_name("Example Holdings, Inc.")=="EXAMPLE"
