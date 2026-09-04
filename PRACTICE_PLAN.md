# 7 次練習規劃

建議每次約 30～60 分鐘。不要一次把所有功能都背起來，重點是每次親手修改並執行。

## 第 1 次：認識 Class、物件與屬性

閱讀 `Book.cs`，找出：

- Class 名稱
- 5 個屬性
- 建構子
- 建立物件的 `new Book(...)`

練習：新增 `Category` 屬性，並讓畫面顯示分類。

## 第 2 次：方法與物件狀態

觀察 `Borrow()`、`Return()` 如何改變：

- `IsBorrowed`
- `BorrowerName`

練習：新增 `Rename(string newTitle)` 方法，禁止把書名改成空字串。

## 第 3 次：封裝 Encapsulation

比較：

```csharp
public bool IsBorrowed { get; set; }
```

與：

```csharp
public bool IsBorrowed { get; private set; }
```

思考為什麼借閱狀態不應讓外部隨意修改。

練習：嘗試在 `Program.cs` 寫 `book.IsBorrowed = true;`，觀察編譯器提示，再把它刪除。

## 第 4 次：Interface

閱讀 `IBorrowable.cs`，理解它只規定功能，不負責實作。

練習：建立 `Magazine` 類別並實作 `IBorrowable`，屬性可包含：

- `Id`
- `Title`
- `IssueNumber`
- `IsBorrowed`
- `BorrowerName`

## 第 5 次：事件 Event

觀察兩個部分：

```csharp
library.BookStatusChanged += HandleBookStatusChanged;
```

這是「訂閱事件」。

```csharp
BookStatusChanged?.Invoke(this, eventArgs);
```

這是「觸發事件」。

練習：在事件通知中增加書籍編號與動作名稱。

## 第 6 次：List 與查詢

閱讀：

- `List<Book>`
- `FirstOrDefault()`
- `Where()`
- `Any()`

練習：新增 `SearchByAuthor(string author)`，可以用作者名稱搜尋。

## 第 7 次：完成自己的小改版

從下面選 2～3 項完成：

1. 新增書籍功能。
2. 刪除書籍功能。
3. 顯示「只看可借閱書籍」。
4. 顯示「只看已借出書籍」。
5. 新增借閱日期 `BorrowedAt`。
6. 新增應還日期 `DueDate`。
7. 借閱超過期限時顯示「已逾期」。

## 完成後自我檢查

你應該能用自己的話回答：

1. Class 和物件有什麼不同？
2. Property 和欄位有什麼不同？
3. Method 為什麼可以保護物件狀態？
4. Interface 解決了什麼問題？
5. 誰觸發事件？誰訂閱事件？
6. 為什麼 `_books` 設為 `private`？
