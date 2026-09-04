namespace SimpleLibraryOop.Events;

/// <summary>
/// 借還書事件所攜帶的資料。
/// </summary>
public class BookStatusChangedEventArgs : EventArgs
{
    public int BookId { get; }

    public string BookTitle { get; }

    public string ActionName { get; }

    public string Message { get; }

    public DateTime OccurredAt { get; }

    public BookStatusChangedEventArgs(
        int bookId,
        string bookTitle,
        string actionName,
        string message)
    {
        BookId = bookId;
        BookTitle = bookTitle;
        ActionName = actionName;
        Message = message;
        OccurredAt = DateTime.Now;
    }
}
