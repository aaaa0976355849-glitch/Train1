using SimpleLibraryOop.Events;
using SimpleLibraryOop.Models;

namespace SimpleLibraryOop.Services;

/// <summary>
/// 圖書館管理類別：集中處理新增、查詢、借書與還書。
/// </summary>
public class LibraryManager
{
    private readonly List<Book> _books = new();

    /// <summary>
    /// 當書籍被借出或歸還時觸發。
    /// </summary>
    public event EventHandler<BookStatusChangedEventArgs>? BookStatusChanged;

    /// <summary>
    /// 對外提供唯讀清單，避免外部直接修改內部 List。
    /// </summary>
    public IReadOnlyList<Book> Books => _books.AsReadOnly();

    public bool AddBook(Book book)
    {
        bool isDuplicate = _books.Any(existingBook => existingBook.Id == book.Id);

        if (isDuplicate)
        {
            return false;
        }

        _books.Add(book);
        return true;
    }

    public Book? FindBookById(int id)
    {
        return _books.FirstOrDefault(book => book.Id == id);
    }

    public IEnumerable<Book> SearchByTitle(string keyword)
    {
        if (string.IsNullOrWhiteSpace(keyword))
        {
            return Array.Empty<Book>();
        }

        return _books.Where(book =>
            book.Title.Contains(keyword.Trim(), StringComparison.OrdinalIgnoreCase));
    }

    public bool BorrowBook(int id, string borrowerName)
    {
        Book? book = FindBookById(id);

        if (book is null || !book.Borrow(borrowerName))
        {
            return false;
        }

        RaiseBookStatusChanged(
            book,
            actionName: "借書",
            message: $"{book.BorrowerName} 已借出《{book.Title}》。");

        return true;
    }

    public bool ReturnBook(int id)
    {
        Book? book = FindBookById(id);

        if (book is null || !book.IsBorrowed)
        {
            return false;
        }

        string borrowerName = book.BorrowerName ?? "未知借閱人";

        if (!book.Return())
        {
            return false;
        }

        RaiseBookStatusChanged(
            book,
            actionName: "還書",
            message: $"{borrowerName} 已歸還《{book.Title}》。");

        return true;
    }

    private void RaiseBookStatusChanged(
        Book book,
        string actionName,
        string message)
    {
        var eventArgs = new BookStatusChangedEventArgs(
            book.Id,
            book.Title,
            actionName,
            message);

        BookStatusChanged?.Invoke(this, eventArgs);
    }
}
