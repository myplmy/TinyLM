# expanded_train:1251504 원형 HOLD

## 분리한 원문 구절

```text
The following ADO.NET architecture diagram demonstrates the ADO.NET component model and how they work together.
The following image illustrates where the Entity Framework fits into our application:
As the image above shows, the Entity Framework fits between business entities (domain classes) and the database. It saves data stored in business entity properties and also retrieves data from the database and automatically converts it to business entity objects.
The following figure shows the general architecture of the Entity Framework.
To make the comparison process easier and to answer many questions about them (eg, "Does the Entity Framework use ADO.NET?" etc.), we provide a clear comparison table.
Comparison table of ADO.NET and Entity Framework
```

## 근거

ADO.NET architecture diagram, Entity Framework image, and Entity Framework architecture figure are announced but no corresponding figure/image contents occur in the text. The sentence stating that the Entity Framework fits between business entities and the database contains a complete relation independent of the absent image; the new text retains that relation and other sentence content while removing only `As the image above shows,`. The comparison-table promise and heading have no table data, so only that direct table-dependent sentence and heading are held. The named ADO.NET and Entity Framework details, real API/code references, comparison conditions, and independent conclusion remain in the body.
