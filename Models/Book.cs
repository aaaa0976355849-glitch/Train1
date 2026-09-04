using SimpleLibraryOop.Interfaces;

namespace SimpleLibraryOop.Models;

/// <summary>
/// 書籍類別：保存書籍資料與借還書狀態。
/// </summary>
public class Book : IBorrowable
{
    // 只能在建立物件時設定，之後不可修改。
    public int Id { get; }

    // 一般可讀寫屬性。
    public string Title { get; set; }

    public string Author { get; set; }

    // 外部只能讀取，只有 Book 自己可以修改。
    public bool IsBorrowed { get; private set; }

    public string? BorrowerName { get; private set; }

    public Book(int id, string title, string author)
    {
        Id = id;
        Title = title;
        Author = author;
    }

    /// <summary>
    /// 借書。成功回傳 true，失敗回傳 false。
    /// </summary>
    public bool Borrow(string borrowerName)
    {
        if (IsBorrowed || string.IsNullOrWhiteSpace(borrowerName))
        {
            return false;
        }

        IsBorrowed = true;
        BorrowerName = borrowerName.Trim();
        return true;
    }

    /// <summary>
    /// 還書。成功回傳 true，失敗回傳 false。
    /// </summary>
    public bool Return()
    {
        if (!IsBorrowed)
        {
            return false;
        }

        IsBorrowed = false;
        BorrowerName = null;
        return true;
    }

    /// <summary>
    /// 將書籍資料整理成適合顯示的文字。
    /// </summary>
    public string GetDisplayText()
    {
        string status = IsBorrowed
            ? $"已借出（借閱人：{BorrowerName}）"
            : "可借閱";

        return $"編號：{Id}｜書名：{Title}｜作者：{Author}｜狀態：{status}";
    }
}
