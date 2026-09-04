# C# 物件導向入門練習：簡易圖書借閱系統

這是一個刻意保持簡單的 Console 專案，適合第一次練習物件導向。

## 你會練到什麼

| 概念 | 專案中的位置 | 用途 |
|---|---|---|
| Class | `Book`、`LibraryManager` | 建立書籍與管理系統的物件 |
| Property | `Title`、`Author`、`IsBorrowed` | 保存物件的資料與狀態 |
| Method | `Borrow()`、`Return()`、`SearchByTitle()` | 讓物件執行工作 |
| Interface | `IBorrowable` | 規定「可借閱物件」必須具備哪些功能 |
| Event | `BookStatusChanged` | 借書或還書成功後主動發出通知 |
| Encapsulation | `private set`、`private readonly List` | 避免外部任意破壞物件狀態 |
| Collection | `List<Book>` | 保存多本書籍 |

## 專案結構

```text
SimpleLibraryOop
├─ Interfaces
│  └─ IBorrowable.cs
├─ Models
│  └─ Book.cs
├─ Events
│  └─ BookStatusChangedEventArgs.cs
├─ Services
│  └─ LibraryManager.cs
├─ Program.cs
├─ PRACTICE_PLAN.md
├─ SimpleLibraryOop.csproj
└─ SimpleLibraryOop.sln
```

## 執行方法

### Visual Studio

1. 開啟 `SimpleLibraryOop.sln`。
2. 按 `Ctrl + F5` 執行。
3. 依照畫面輸入 0～4。

### Visual Studio Code 或終端機

在專案資料夾執行：

```bash
dotnet run
```

## 建議閱讀順序

1. `Interfaces/IBorrowable.cs`
2. `Models/Book.cs`
3. `Events/BookStatusChangedEventArgs.cs`
4. `Services/LibraryManager.cs`
5. `Program.cs`

## 事件的執行流程

```text
使用者選擇借書
    ↓
Program 呼叫 LibraryManager.BorrowBook()
    ↓
LibraryManager 呼叫 Book.Borrow()
    ↓
借閱成功後觸發 BookStatusChanged 事件
    ↓
Program 的 HandleBookStatusChanged() 收到通知並顯示文字
```

## 初次執行時可以測試

1. 顯示全部書籍。
2. 借出編號 1，借閱人輸入自己的名字。
3. 再次顯示全部書籍，觀察狀態改變。
4. 再借一次編號 1，觀察失敗訊息。
5. 歸還編號 1。
6. 搜尋「物件」或「C#」。

## 初學者提醒

- `class` 是設計圖，`new Book(...)` 才是依設計圖建立出的物件。
- 屬性保存狀態，方法改變或使用狀態。
- `private set` 表示外部可以讀取，但不能直接修改。
- Interface 不是實際物件，而是一份共同規格。
- Event 的重點是「發生某件事時，通知已訂閱的人」。

更完整的學習步驟請看 [`PRACTICE_PLAN.md`](./PRACTICE_PLAN.md)。
