# Ghuluww (Exaggeration) in al-Kāfī: A Data-Analytic Approach
## Authors
Kaveh Aryanpoo<sup>1</sup>, Mohammad Reza Mousavi<sup>1</sup>, ​1 Mostafa Movahedifar<sup>2</sup>



<sup><sup>1</sup> King’s College London, London, UK</sup>  <sup>   </sup>   <sup><sup>2</sup> Al-Mahdi Institute, Birmingham, UK</sup>

## Abstract
The focus of the present study is the concept of ghuluww (to transgress a boundary) tendency and the ḥadīth content ascribed to this tendency. We designate ḥadīth transmitters that were labelled as the subscribers of the idea of ghuluww, called ghulāt (sing. ghālī; transgressive Shīʿīs), who lived in the early Islamic era, especially during the Imamates of the fifth and sixth Shīʿī Imāms, Muḥammad b. Alī al-Bāqir (d. 114/733) and Jafar b. Muḥammad al-Sādiq (d. 148/765). We examine such associations considering the 5th/11th-century bio-bibliographical dictionaries.


## How to Run

Follow the instructions on [this](https://colab.research.google.com/drive/1qvpvJxSif2aIswGVVOuDI2K1G-Tbw8yR?usp=sharing) Jupyter notebook.

## Database Tables Documentation

### 1. Hadith

This table represents individual Hadith entries.

| Column       | Type    | Description                           |
|--------------|---------|---------------------------------------|
| ID           | INTEGER | Unique identifier for each Hadith     |
| BookName     | TEXT    | Name of the book containing the Hadith|
| SectionName  | TEXT    | Specific section within the book      |

---

### 2. Isnad

This table represents the chains of transmission (Isnad) for each Hadith.

| Column          | Type    | Description                                      |
|-----------------|---------|--------------------------------------------------|
| ID              | INTEGER | Unique identifier for each Isnad                 |
| HadithID        | INTEGER | Corresponding ID from the Hadith table           |
| TransmitterIDs  | TEXT    | Comma-separated list of transmitter IDs          |

---

### 3. Transmitter

This table contains details about the transmitters in the Isnad.

| Column  | Type    | Description                                 |
|---------|---------|---------------------------------------------|
| ID      | INTEGER | Unique identifier for each transmitter      |
| ID__1   | INTEGER | Secondary ID or reference number (if any)   |
| Name    | TEXT    | Name of the transmitter                     |

